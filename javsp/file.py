"""与文件相关的各类功能"""
import os
from pathlib import Path
import re
import ctypes
import logging
import itertools
import json
from sys import platform
from typing import List


__all__ = ['scan_movies', 'get_fmt_size', 'get_remaining_path_len', 'replace_illegal_chars', 'get_failed_when_scan', 'find_subtitle_in_dir']


from javsp.avid import *
from javsp.lib import re_escape
from javsp.config import Cfg
from javsp.datatype import Movie

logger = logging.getLogger(__name__)
failed_items = []


def scan_movies(root: str) -> List[Movie]:
    """获取文件夹内的所有影片的列表（自动探测同一文件夹内的分片）"""
    # 由于实现的限制: 
    # 1. 以数字编号最多支持10个分片，字母编号最多支持26个分片
    # 2. 允许分片间的编号有公共的前导符（如编号01, 02, 03），因为求prefix时前导符也会算进去

    # 扫描所有影片文件并获取它们的番号
    dic = {}    # avid: [abspath1, abspath2...]
    small_videos = {}
    ignore_folder_name_pattern = re.compile('|'.join(Cfg().scanner.ignored_folder_name_pattern))
    for dirpath, dirnames, filenames in os.walk(root):
        for name in dirnames.copy():
            if ignore_folder_name_pattern.match(name):
                dirnames.remove(name)
        for file in filenames:
            ext = os.path.splitext(file)[1].lower()
            if ext in Cfg().scanner.filename_extensions:
                fullpath = os.path.join(dirpath, file)
                # 忽略小于指定大小的文件
                filesize = os.path.getsize(fullpath)
                if filesize < Cfg().scanner.minimum_size:
                    small_videos.setdefault(file, []).append(fullpath)
                    continue
                dvdid = get_id(fullpath)
                cid = get_cid(fullpath)
                # 如果文件名能匹配到cid，那么将cid视为有效id，因为此时dvdid多半是错的
                avid = cid if cid else dvdid
                if avid:
                    if avid in dic:
                        dic[avid].append(fullpath)
                    else:
                        dic[avid] = [fullpath]
                else:
                    fail = Movie('无法识别番号')
                    fail.files = [fullpath]
                    failed_items.append(fail)
                    # 改为debug级别，避免输出过多错误信息
                    logger.debug(f"无法提取影片番号: '{fullpath}'")
    # 多分片影片容易有文件大小低于阈值的子片，进行特殊处理
    has_avid = {}
    for name in list(small_videos.keys()):
        dvdid = get_id(name)
        cid = get_cid(name)
        avid = cid if cid else dvdid
        if avid in dic:
            dic[avid].extend(small_videos.pop(name))
        elif avid:
            has_avid[name] = avid
    # 对于前面忽略的视频生成一个简单的提示
    small_videos = {k:sorted(v) for k,v in sorted(small_videos.items())}
    skipped_files = list(itertools.chain(*small_videos.values()))
    skipped_cnt = len(skipped_files)
    if skipped_cnt > 0:
        if len(has_avid) > 0:
            logger.info(f"跳过了 {', '.join(has_avid)} 等{skipped_cnt}个小于指定大小的视频文件")
        else:
            logger.info(f"跳过了{skipped_cnt}个小于指定大小的视频文件")
        logger.debug('跳过的视频文件如下:\n' + '\n'.join(skipped_files))
    # 检查是否有多部影片对应同一个番号
    non_slice_dup = {}  # avid: [abspath1, abspath2...]
    for avid, files in dic.copy().items():
        # 一一对应的直接略过
        if len(files) == 1:
            continue
        dirs = set([os.path.split(i)[0] for i in files])
        # 不同位置的多部影片有相同番号时，略过并报错
        if len(dirs) > 1:
            non_slice_dup[avid] = files
            del dic[avid]
            continue
        
        # 特殊处理：动漫影片的多语言版本
        # 检查是否是动漫影片（番号以ANIME:开头）
        if avid.startswith('ANIME:'):
            # 对于动漫影片，检查是否是不同语言版本（chs, cht等）
            basenames = [os.path.basename(i) for i in files]
            
            # 检查文件名是否包含语言标记
            language_patterns = [r'\.chs\.', r'\.cht\.', r'\.简中\.', r'\.繁中\.', r'\.简体\.', r'\.繁体\.']
            has_language_versions = False
            for pattern in language_patterns:
                if any(re.search(pattern, name, re.I) for name in basenames):
                    has_language_versions = True
                    break
            
            # 检查是否是分片（包含CD, Part, 数字后缀等）
            is_slice = False
            slice_patterns = [
                r'[-_\s]CD[-_\s]*\d',
                r'[-_\s]Part[-_\s]*\d',
                r'[-_\s]\d{1,3}\.',
                r'[-_\s][A-Za-z]\.[a-zA-Z0-9]+$'
            ]
            for pattern in slice_patterns:
                if any(re.search(pattern, name, re.I) for name in basenames):
                    is_slice = True
                    break
            
            # 如果是动漫多语言版本，保留所有文件
            # 对于动漫多语言版本，直接接受，不进行分片识别
            if has_language_versions and not is_slice:
                logger.debug(f"识别为动漫多语言版本（非分片）: {avid}, 文件数: {len(files)}")
                # 按语言版本排序：raw/mkv优先，然后chs，最后cht
                def language_priority(filename):
                    filename_lower = filename.lower()
                    if '.mkv' in filename_lower and not any(p in filename_lower for p in ['.chs.', '.cht.', '.简中.', '.繁中.']):
                        return 0  # raw版本
                    elif '.chs.' in filename_lower or '.简中.' in filename_lower:
                        return 1  # 简体中文
                    elif '.cht.' in filename_lower or '.繁中.' in filename_lower:
                        return 2  # 繁体中文
                    else:
                        return 3  # 其他
                
                files.sort(key=lambda x: language_priority(os.path.basename(x)))
                dic[avid] = files
                continue  # 跳过后续的分片识别逻辑
        # 提取分片信息（改进版，支持多字符分片标识）
        basenames = [os.path.basename(i) for i in files]
        prefix = os.path.commonprefix(basenames)
        
        # 改进的正则表达式：支持多字符分片标识
        patterns = [
            # 模式1: 共同前缀后跟可选分隔符和数字（1-3位）
            re_escape(prefix) + r'[-_\s]*(\d{1,3})',
            # 模式2: 共同前缀后跟CD和数字
            re_escape(prefix) + r'[-_\s]*CD[-_\s]*(\d{1,3})',
            # 模式3: 共同前缀后跟单个字母
            re_escape(prefix) + r'[-_\s]*([a-zA-Z])',
            # 模式4: 共同前缀后跟part和数字
            re_escape(prefix) + r'[-_\s]*PART[-_\s]*(\d{1,3})',
        ]
        
        slice_numbers = []
        postfixes = []
        has_explicit_slice = [False] * len(basenames)
        
        # 第一遍：识别有明确分片标识的文件
        for i, name in enumerate(basenames):
            matched = False
            for pattern in patterns:
                try:
                    match = re.search(pattern, name, re.I)
                except re.error:
                    logger.debug(f"正则识别影片分片信息时出错: '{pattern}'")
                    continue
                
                if match:
                    slice_id = match.group(1)
                    # 提取剩余部分（分片标识之后的部分）
                    remaining = name[match.end():]
                    slice_numbers.append(slice_id)
                    postfixes.append(remaining)
                    has_explicit_slice[i] = True
                    matched = True
                    break
            
            if not matched:
                # 暂时标记为None，第二遍处理
                slice_numbers.append(None)
                postfixes.append(None)
        
        # 第二遍：处理没有明确分片标识的文件
        for i in range(len(basenames)):
            if slice_numbers[i] is None:
                name = basenames[i]
                # 检查是否正好是共同前缀（没有分片标识）
                if name.startswith(prefix):
                    remaining = name[len(prefix):]
                    # 检查是否已经有明确的分片1
                    has_slice_1 = False
                    for j in range(len(basenames)):
                        if has_explicit_slice[j] and slice_numbers[j] == '1':
                            has_slice_1 = True
                            break
                    
                    if not has_slice_1:
                        # 没有明确的分片1，假设这是分片1
                        slice_numbers[i] = '1'
                        postfixes[i] = remaining
                        has_explicit_slice[i] = False  # 这是推断的，不是明确的
                    else:
                        # 已经有明确的分片1，这个文件无法识别
                        logger.debug(f"无法识别分片信息: 文件 '{name}' 没有分片标识，但已有明确的分片1")
                        slice_numbers[i] = None
                        postfixes[i] = None
                else:
                    # 无法识别
                    slice_numbers[i] = None
                    postfixes[i] = None
        
        # 检查是否有None值
        if any(x is None for x in slice_numbers):
            # 对于动漫影片，如果没有分片标识，可能是多语言版本
            # 为每个文件分配基于语言版本的标识符
            if avid.startswith('ANIME:'):
                logger.debug(f"动漫影片无分片标识，尝试按语言版本处理: {prefix=}")
                # 重新分配slice_numbers基于语言版本
                for i, name in enumerate(basenames):
                    filename_lower = name.lower()
                    if '.chs.' in filename_lower or '.简中.' in filename_lower:
                        slice_numbers[i] = 'chs'
                    elif '.cht.' in filename_lower or '.繁中.' in filename_lower:
                        slice_numbers[i] = 'cht'
                    elif '.mkv' in filename_lower and not any(p in filename_lower for p in ['.chs.', '.cht.', '.简中.', '.繁中.']):
                        slice_numbers[i] = 'raw'
                    else:
                        slice_numbers[i] = f'file{i}'
                
                # 检查是否还有None值
                if any(x is None for x in slice_numbers):
                    logger.debug(f"无法识别分片信息: {prefix=}, {slice_numbers=}")
                    non_slice_dup[avid] = files
                    del dic[avid]
                    continue
            else:
                logger.debug(f"无法识别分片信息: {prefix=}, {slice_numbers=}")
                non_slice_dup[avid] = files
                del dic[avid]
                continue
        
        # 检查后缀是否一致
        # 对于动漫影片，允许不同的语言版本后缀（.chs.mp4, .cht.mp4, .mkv等）
        if len(set(postfixes)) != 1:
            # 检查是否是动漫影片
            if avid.startswith('ANIME:'):
                # 对于动漫影片，检查后缀差异是否只是语言版本差异
                # 提取所有后缀的文件扩展名部分
                extensions = []
                for postfix in postfixes:
                    # 提取文件扩展名（最后一个点之后的部分）
                    if '.' in postfix:
                        ext = postfix[postfix.rfind('.'):].lower()
                        extensions.append(ext)
                    else:
                        extensions.append('')
                
                # 检查扩展名是否都是视频格式
                video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg']
                all_video_ext = all(ext in video_extensions for ext in extensions)
                
                if all_video_ext:
                    # 所有都是视频格式，可能是不同语言版本
                    logger.debug(f"动漫影片允许不同的语言版本后缀: {set(postfixes)}")
                else:
                    logger.debug(f"无法识别分片信息: 后缀不一致 {set(postfixes)}")
                    non_slice_dup[avid] = files
                    del dic[avid]
                    continue
            else:
                logger.debug(f"无法识别分片信息: 后缀不一致 {set(postfixes)}")
                non_slice_dup[avid] = files
                del dic[avid]
                continue
        
        # 检查分片标识是否唯一
        if len(slice_numbers) != len(set(slice_numbers)):
            logger.debug(f"无法识别分片信息: 分片标识重复 {slice_numbers}")
            non_slice_dup[avid] = files
            del dic[avid]
            continue
        
        # 转换分片标识为数字
        numeric_slices = []
        for s in slice_numbers:
            if s.isdigit():
                numeric_slices.append(int(s))
            elif s.isalpha() and len(s) == 1:
                # 字母转数字：a=1, b=2, ...
                numeric_slices.append(ord(s.lower()) - ord('a') + 1)
            else:
                # 尝试提取数字部分（如CD10中的10）
                num_match = re.search(r'(\d+)', s)
                if num_match:
                    numeric_slices.append(int(num_match.group(1)))
                else:
                    # 处理语言版本标识符（chs, cht, raw等）
                    # 为语言版本分配固定的数字值
                    if s.lower() == 'raw':
                        numeric_slices.append(0)  # raw版本优先级最高
                    elif s.lower() == 'chs':
                        numeric_slices.append(1)  # 简体中文
                    elif s.lower() == 'cht':
                        numeric_slices.append(2)  # 繁体中文
                    elif s.startswith('file'):
                        # 文件标识符，提取数字部分
                        file_num_match = re.search(r'file(\d+)', s.lower())
                        if file_num_match:
                            numeric_slices.append(int(file_num_match.group(1)) + 10)  # 从10开始
                        else:
                            numeric_slices.append(99)  # 默认值
                    else:
                        logger.debug(f"无法转换分片标识: {s}")
                        non_slice_dup[avid] = files
                        del dic[avid]
        # 生成最终的分片信息
        sorted_indices = sorted(range(len(numeric_slices)), key=lambda i: numeric_slices[i])
        mapped_files = [files[i] for i in sorted_indices]
        dic[avid] = mapped_files

    # 汇总输出错误提示信息
    msg = ''
    for avid, files in non_slice_dup.items():
        msg += f'{avid}: \n'
        for f in files:
            msg += ('  ' + os.path.relpath(f, root) + '\n')
    if msg:
        logger.error("下列番号对应多部影片文件且不符合分片规则，已略过整理，请手动处理后重新运行脚本: \n" + msg)
    # 转换数据的组织格式
    movies: List[Movie] = []
    for avid, files in dic.items():
        src = guess_av_type(avid)
        if src != 'cid':
            mov = Movie(avid)
        else:
            mov = Movie(cid=avid)
            # 即使初步识别为cid，也存储dvdid以供误识别时退回到dvdid模式进行抓取
            mov.dvdid = get_id(files[0])
        mov.files = files
        mov.data_src = src
        logger.debug(f'影片数据源类型: {avid}: {src}')
        movies.append(mov)
    return movies


def get_failed_when_scan():
    """获取扫描影片过程中无法自动识别番号的条目"""
    return failed_items


_PARDIR_REPLACE = re.compile(r'\.{2,}')
def replace_illegal_chars(name):
    """将不能用于文件名的字符替换为形近的字符"""
    # 非法字符列表 https://stackoverflow.com/a/31976060/6415337
    if platform == 'win32': 
        # http://www.unicode.org/Public/security/latest/confusables.txt
        charmap = {'<': '❮',
                   '>': '❯',
                   ':': '：',
                   '"': '″',
                   '/': '／',
                   '\\': '＼',
                   '|': '｜',
                   '?': '？',
                   '*': '꘎'}
        for c, rep in charmap.items():
            name = name.replace(c, rep)
    elif platform == "darwin":  # MAC OS X
        name = name.replace(':', '：')
    else:   # 其余都当做Linux处理
        name = name.replace('/', '／')
    # 处理连续多个英文句点.
    if os.pardir in name:
        name = _PARDIR_REPLACE.sub('…', name)
    return name


def is_remote_drive(path: str):
    """判断一个路径是否为远程映射到本地"""
    #TODO: 当前仅支持Windows平台
    if platform != 'win32':
        return False
    DRIVE_REMOTE = 0x4
    drive = os.path.splitdrive(os.path.abspath(path))[0] + os.sep
    result = ctypes.windll.kernel32.GetDriveTypeW(drive)
    return result == DRIVE_REMOTE


def get_remaining_path_len(path):
    """计算当前系统支持的最大路径长度与给定路径长度的差值"""
    #TODO: 支持不同的操作系统
    fullpath = os.path.abspath(path)
    # Windows: If the length exceeds ~256 characters, you will be able to see the path/files via Windows/File Explorer, but may not be able to delete/move/rename these paths/files
    length = len(fullpath.encode('utf-8')) if Cfg().summarizer.path.length_by_byte else len(fullpath)
    remaining = Cfg().summarizer.path.length_maximum - length
    return remaining


def get_fmt_size(file_or_size) -> str:
    """获取格式化后的文件大小

    Args:
        file_or_size (str or int): 文件路径或者文件大小

    Returns:
        str: e.g. 20.21 MiB
    """
    if isinstance(file_or_size, (int, float)):
        size = file_or_size
    else:
        size = os.path.getsize(file_or_size)
    for unit in ['','Ki','Mi','Gi','Ti']:
        # 1023.995: to avoid rounding bug when format str, e.g. 1048571 -> 1024.0 KiB
        if abs(size) < 1023.995:
            return f"{size:3.2f} {unit}B"
        size /= 1024.0


_sub_files = {}
SUB_EXTENSIONS = ('.srt', '.ass')
def find_subtitle_in_dir(folder: str, dvdid: str):
    """在folder内寻找是否有匹配dvdid的字幕"""
    folder_data = _sub_files.get(folder)
    if folder_data is None:
        # 此文件夹从未检查过时
        folder_data = {}
        for dirpath, dirnames, filenames in os.walk(folder):
            for file in filenames:
                basename, ext = os.path.splitext(file)
                if ext in SUB_EXTENSIONS:
                    match_id = get_id(basename)
                    if match_id:
                        folder_data[match_id.upper()] = os.path.join(dirpath, file)
        _sub_files[folder] = folder_data
    sub_file = folder_data.get(dvdid.upper())
    return sub_file


if __name__ == "__main__":
    p = "C:/Windows\\System32//PerceptionSimulation\\..\\Assets\\/ClosedHand.png"
    print(get_remaining_path_len(p))
