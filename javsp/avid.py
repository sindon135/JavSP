"""获取和转换影片的各类番号（DVD ID, DMM cid, DMM pid）"""
import os
import re
from pathlib import Path


__all__ = ['get_id', 'get_cid', 'guess_av_type']


from javsp.config import Cfg

def get_id(filepath_str: str) -> str:
    """从给定的文件路径中提取番号（DVD ID）"""
    filepath = Path(filepath_str)
    # 通常是接收文件的路径，当然如果是普通字符串也可以
    ignore_pattern = re.compile('|'.join(Cfg().scanner.ignored_id_pattern))
    norm = ignore_pattern.sub('', filepath.stem).upper()
    if 'FC2' in norm:
        # 根据FC2 Club的影片数据，FC2编号为5-7个数字
        match = re.search(r'FC2[^A-Z\d]{0,5}(PPV[^A-Z\d]{0,5})?(\d{5,7})', norm, re.I)
        if match:
            return 'FC2-' + match.group(2)
    elif 'HEYDOUGA' in norm:
        match = re.search(r'(HEYDOUGA)[-_]*(\d{4})[-_]0?(\d{3,5})', norm, re.I)
        if match:
            return '-'.join(match.groups())
    elif 'GETCHU' in norm:
        match = re.search(r'GETCHU[-_]*(\d+)', norm, re.I)
        if match:
            return 'GETCHU-' + match.group(1)
    elif 'GYUTTO' in norm:
        match = re.search(r'GYUTTO-(\d+)', norm, re.I)
        if match:
            return 'GYUTTO-' + match.group(1)
    elif '259LUXU' in norm: # special case having form of '259luxu'
        match = re.search(r'259LUXU-(\d+)', norm, re.I)
        if match:
            return '259LUXU-' + match.group(1)

    else:
        # 先尝试移除可疑域名进行匹配，如果匹配不到再使用原始文件名进行匹配
        no_domain = re.sub(r'\w{3,10}\.(COM|NET|APP|XYZ)', '', norm, flags=re.I)
        if no_domain != norm:
            avid = get_id(no_domain)
            if avid:
                return avid
        # 匹配缩写成hey的heydouga影片。由于番号分三部分，要先于后面分两部分的进行匹配
        match = re.search(r'(?:HEY)[-_]*(\d{4})[-_]0?(\d{3,5})', norm, re.I)
        if match:
            return 'heydouga-' + '-'.join(match.groups())
        # 匹配片商 MUGEN 的奇怪番号。由于MK3D2DBD的模式，要放在普通番号模式之前进行匹配
        match = re.search(r'(MKB?D)[-_]*(S\d{2,3})|(MK3D2DBD|S2M|S2MBD)[-_]*(\d{2,3})', norm, re.I)
        if match:
            if match.group(1) is not None:
                avid = match.group(1) + '-' + match.group(2)
            else:
                avid = match.group(3) + '-' + match.group(4)
            return avid
        # 匹配IBW这样带有后缀z的番号
        match = re.search(r'(IBW)[-_](\d{2,5}z)', norm, re.I)
        if match:
            return match.group(1) + '-' + match.group(2)
        # 普通番号，优先尝试匹配带分隔符的（如ABC-123）
        match = re.search(r'([A-Z]{2,10})[-_](\d{2,5})', norm, re.I)
        if match:
            return match.group(1) + '-' + match.group(2)
        # 普通番号，运行到这里时表明无法匹配到带分隔符的番号
        # 先尝试匹配东热的red, sky, ex三个不带-分隔符的系列
        # （这三个系列已停止更新，因此根据其作品编号将数字范围限制得小一些以降低误匹配概率）
        match = re.search(r'(RED[01]\d\d|SKY[0-3]\d\d|EX00[01]\d)', norm, re.I)
        if match:
            return match.group(1)
        # 然后再将影片视作缺失了-分隔符来匹配
        match = re.search(r'([A-Z]{2,})(\d{2,5})', norm, re.I)
        if match:
            return match.group(1) + '-' + match.group(2)
    # 尝试匹配TMA制作的影片（如'T28-557'，他家的番号很乱）
    match = re.search(r'(T[23]8[-_]\d{3})', norm)
    if match:
        return match.group(1)
    # 尝试匹配东热n, k系列
    match = re.search(r'(N\d{4}|K\d{4})', norm, re.I)
    if match:
        return match.group(1)
    # 尝试匹配纯数字番号（无码影片）
    match = re.search(r'(\d{6}[-_]\d{2,3})', norm)
    if match:
        return match.group(1)
    # 如果还是匹配不了，尝试将')('替换为'-'后再试，少部分影片的番号是由')('分隔的
    if ')(' in norm:
        avid = get_id(norm.replace(')(', '-'))
        if avid:
            return avid
    
    # 新增：尝试匹配欧美番号格式（包含点号）
    # 欧美番号格式：系列.日期.演员.标题 或 系列.日期.标题
    # 示例：rkprime.25.11.18.zoey.uso.fucking.at.the.frat
    # 使用原始文件名（未转换为大写）进行匹配
    original_stem = filepath.stem
    western_pattern = re.search(r'([a-z]+\.\d{1,2}\.\d{1,2}\.\d{1,2}\.[a-z.]+)', original_stem.lower())
    if western_pattern:
        return 'WESTERN:' + western_pattern.group(1)
    
    western_pattern = re.search(r'([a-z]+\.\d{1,2}\.\d{1,2}\.[a-z.]+)', original_stem.lower())
    if western_pattern:
        return 'WESTERN:' + western_pattern.group(1)
    
    western_pattern = re.search(r'([a-z]+\.[a-z.]+)', original_stem.lower())
    if western_pattern:
        # 确保不是普通AV番号（如abc-123）
        if not re.search(r'[a-z]+\-\d+', original_stem.lower()):
            return 'WESTERN:' + western_pattern.group(1)
    
    # 新增：改进动漫文件名识别
    # 策略：提取符合命名规范的标题，去除[某某工作组] [某某网站] 这些视频传播者的附加信息
    # 保留原始标题中的OVA、THE ANIMATION等关键词
    
    # 首先尝试匹配标准动漫番号格式（如GLOD-305）
    anime_id_pattern = re.search(r'([A-Z]{2,10}[-_]\d{2,5})', norm)
    if anime_id_pattern:
        # 检查是否是动漫前缀
        anime_prefixes = ['GLOD', 'HUNTB', 'ANIM', 'OVA', 'HODV', 'HMN', 'HND', 'HONE',
                         'JDXA', 'KAGU', 'KIDM', 'KIDZ', 'MILD', 'MIMK', 'MIRD', 'MIST', 'MUM',
                         'NACR', 'NATR', 'NOP', 'NTR', 'OAE', 'OBA', 'OBD', 'OBE', 'OBS',
                         'OCC', 'OCE', 'OCU', 'ODE', 'ODV', 'OFA', 'OFJE', 'OGPP', 'OGR',
                         'OHD', 'OIN', 'OKI', 'OKS', 'OLB', 'OLD', 'OMC', 'OME', 'OMF',
                         'OMG', 'OMH', 'OMI', 'OMK', 'OMM', 'OMN', 'OMO', 'OMU', 'OMX',
                         'ONI', 'ONYX', 'OOP', 'OOT', 'OPC', 'OPD', 'OPE', 'OPF',
                         'OPG', 'OPH', 'OPI', 'OPJ', 'OPK', 'OPL', 'OPM', 'OPN', 'OPO',
                         'OPP', 'OPQ', 'OPR', 'OPS', 'OPT', 'OPU', 'OPV', 'OPW', 'OPX',
                         'OPY', 'OPZ', 'ORC', 'ORD', 'ORE', 'ORF', 'ORG', 'ORH', 'ORI',
                         'ORJ', 'ORK', 'ORL', 'ORM', 'ORN', 'ORO', 'ORP', 'ORQ', 'ORR',
                         'ORS', 'ORT', 'ORU', 'ORV', 'ORW', 'ORX', 'ORY', 'ORZ', 'OSR',
                         'OTD', 'OTK', 'OTM', 'OTN', 'OTO', 'OTP', 'OTR', 'OTS', 'OTT',
                         'OTU', 'OTV', 'OTW', 'OTX', 'OTY', 'OTZ', 'OVG', 'OVS', 'OWA',
                         'OWD', 'OWE', 'OWG', 'OWH', 'OWI', 'OWJ', 'OWK', 'OWL', 'OWM',
                         'OWN', 'OWO', 'OWP', 'OWQ', 'OWR', 'OWS', 'OWT', 'OWU', 'OWV',
                         'OWW', 'OWX', 'OWY', 'OWZ']
        for prefix in anime_prefixes:
            if anime_id_pattern.group(1).upper().startswith(prefix):
                return anime_id_pattern.group(1)
    
    # 简化动漫标题提取：直接提取最后一个]之后的内容作为标题
    # 这可以去除[工作组][网站]等传播者信息
    if ']' in original_stem:
        # 找到最后一个]的位置
        last_bracket = original_stem.rfind(']')
        if last_bracket < len(original_stem) - 1:
            title = original_stem[last_bracket + 1:].strip()
            
            # 检查是否包含动漫关键词或来自动漫厂商
            # 扩展动漫关键词列表
            anime_keywords = ['ANIMATION', 'OVA', 'OAD', 'THE ANIMATION', 'アニメ', r'第\d+話', r'第\d+巻', r'＃\d+', '話', '巻']
            has_anime_keyword = any(re.search(keyword, title, re.IGNORECASE) for keyword in anime_keywords)
            
            # 检查厂商是否是动漫厂商
            # 提取最后一个]之前的内容作为可能的厂商信息
            before_last_bracket = original_stem[:last_bracket]
            brackets_content = re.findall(r'\[([^\]]+)\]', before_last_bracket)
            studio = brackets_content[-1] if brackets_content else ''
            
            # 动漫厂商列表（扩展）
            anime_studios = ['Queen Bee', 'ピンクパイナップル', 'nur', '魔人', 'ショーテン', 'メリー・ジェーン', 
                           'ばにぃうぉ～か～', 'あんてきぬすっ', 'ショーテ ン', 'メリー・ジェーン',
                           'Queen', 'Bee', 'ピンク', 'パイナップル']
            is_anime_studio = any(studio.lower().find(anime_studio.lower()) != -1 for anime_studio in anime_studios)
            
            # 检查是否包含日文字符（动漫标题通常包含日文）
            has_japanese_chars = bool(re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', title))
            
            if has_anime_keyword or is_anime_studio or (has_japanese_chars and ']' in original_stem):
                # 清理标题：移除分辨率、字幕标记等
                title = re.sub(r'\d{3,4}[x×]\d{3,4}[pP]?[_\.]?', '', title)
                title = re.sub(r'\[?(中文字幕|字幕|简体|繁体|简繁|CHS|CHT|BIG5|GB)\]?', '', title, flags=re.IGNORECASE)
                title = re.sub(r'\s+', ' ', title).strip()
                title = re.sub(r'^[\.\-_\s]+|[\.\-_\s]+$', '', title)
                
                # 在提取番号前，先移除分片标识（CD1, CD2等）
                # 但保留在标题中用于后续分片识别
                clean_title_for_id = title
                # 移除常见的分片标识
                clean_title_for_id = re.sub(r'[-_\s]*(CD|Part|PART|DISC|DISK|DVD|BD|DISK|DISC)[-__\s]*\d+', '', clean_title_for_id, flags=re.IGNORECASE)
                clean_title_for_id = re.sub(r'[-_\s]*\d+$', '', clean_title_for_id)  # 移除末尾的数字
                clean_title_for_id = clean_title_for_id.strip()
                
                # 提取可能的番号
                id_in_title = re.search(r'([A-Z]{2,10}[-_]\d{2,5})', clean_title_for_id.upper())
                if id_in_title:
                    return id_in_title.group(1)
                
                # 简化标题：移除常见的分卷标记，但保留OVA等关键词
                # 注意：这里只移除分卷标记，保留OVA等关键词
                simplified_title = clean_title_for_id[:80].strip()
                if simplified_title:
                    return f'ANIME:{simplified_title}'
    
    # 尝试匹配简单的OVA文件名（没有括号的格式）
    # 如：OVAクラスで男は僕一人！？ ＃1.mkv
    simple_ova_pattern = re.search(r'^(OVA|OAD)[^\[\]]+?(?:第\d+[話巻]|＃\d+)', original_stem, re.IGNORECASE)
    if simple_ova_pattern:
        title = original_stem
        # 清理标题
        title = re.sub(r'\d{3,4}[x×]\d{3,4}[pP]?[_\.]?', '', title)
        title = re.sub(r'\[?(中文字幕|字幕|简体|繁体|简繁|CHS|CHT|BIG5|GB)\]?', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s+', ' ', title).strip()
        title = re.sub(r'^[\.\-_\s]+|[\.\-_\s]+$', '', title)
        
        # 提取可能的番号
        id_in_title = re.search(r'([A-Z]{2,10}[-_]\d{2,5})', title.upper())
        if id_in_title:
            return id_in_title.group(1)
        
        simplified_title = title[:80].strip()
        if simplified_title:
            return f'ANIME:{simplified_title}'
    
    # 如果最后仍然匹配不了番号，则尝试使用文件所在文件夹的名字去匹配
    if filepath.parent.name != '': # haven't reach '.' or '/'
        return get_id(filepath.parent.name)
    else:
        return ''


CD_POSTFIX = re.compile(r'([-_]\w|cd\d)$')
def get_cid(filepath: str) -> str:
    """尝试将给定的文件名匹配为CID（Content ID）"""
    basename = os.path.splitext(os.path.basename(filepath))[0]
    # 移除末尾可能带有的分段影片序号
    possible = CD_POSTFIX.sub('', basename)
    # cid只由数字、小写字母和下划线组成
    match = re.match(r'^([a-z\d_]+)$', possible, re.A)
    if match:
        possible = match.group(1)
        if '_' not in possible:
            # 长度为7-14的cid就占了约99.01%. 最长的cid为24，但是长为20-24的比例不到十万分之五
            match = re.match(r'^[a-z\d]{7,19}$', possible)
            if match:
                return possible
        else:
            # 绝大多数都只有一个下划线（只有约万分之一带有两个下划线）
            match2 = re.match(r'''^h_\d{3,4}[a-z]{1,10}\d{2,5}[a-z\d]{0,8}$  # 约 99.17%
                                |^\d{3}_\d{4,5}$                            # 约 0.57%
                                |^402[a-z]{3,6}\d*_[a-z]{3,8}\d{5,6}$       # 约 0.09%
                                |^h_\d{3,4}wvr\d\w\d{4,5}[a-z\d]{0,8}$      # 约 0.06%
                                 $''', possible, re.VERBOSE)
            if match2:
                return possible
    return ''


def guess_av_type(avid: str) -> str:
    """识别给定的番号所属的分类: normal, fc2, cid, anime, western"""
    match = re.match(r'^FC2-\d{5,7}$', avid, re.I)
    if match:
        return 'fc2'
    match = re.match(r'^GETCHU-(\d+)',avid,re.I)
    if match:
        return 'getchu'
    match = re.match(r'^GYUTTO-(\d+)',avid,re.I)
    if match:
        return 'gyutto'
    # 如果传入的avid完全匹配cid的模式，则将影片归类为cid
    cid = get_cid(avid)
    if cid == avid:
        return 'cid'
    
    # 检查是否以ANIME:开头（来自get_id函数的识别结果）
    avid_upper = avid.upper()
    if avid_upper.startswith('ANIME:'):
        return 'anime'
    
    # 新增：欧美番号识别
    # 欧美番号通常包含点号，或者有特定格式
    if '.' in avid and not avid_upper.startswith('FC2'):
        # 进一步检查是否为欧美格式
        # 常见欧美厂商/系列模式
        western_patterns = [
            r'RKPrime', r'Brazzers', r'RealityKings', r'BangBros', r'NaughtyAmerica',
            r'TeamSkeet', r'PropertySex', r'PublicAgent', r'DDFNetwork',
            r'X-Art', r'MetArt', r'WowGirls', r'VivThomas', r'FakeTaxi',
            r'Blacked', r'BlackedRaw', r'Tushy', r'Vixen', r'Deeper',
            r'Slayed', r'Nubiles', r'FTVMilfs', r'MomsTeachSex'
        ]
        for pattern in western_patterns:
            if re.search(pattern, avid, re.I):
                return 'western'
        # 如果包含点号且不是FC2，也归类为western
        return 'western'
    
    # 以上都不是: 默认归类为normal
    return 'normal'


if __name__ == "__main__":
    print(get_id('FC2-123456/Unknown.mp4'))
