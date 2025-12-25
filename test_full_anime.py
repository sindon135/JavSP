#!/usr/bin/env python3
"""测试完整的动漫刮削流程"""
import os
import sys
import tempfile
import shutil
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from javsp.avid import get_id, guess_av_type
from javsp.file import scan_movies

def create_test_files():
    """创建测试文件"""
    test_dir = tempfile.mkdtemp(prefix="javsp_test_")
    print(f"创建测试目录: {test_dir}")
    
    # 创建几个测试文件
    test_files = [
        "[中文字幕][Queen Bee]純情デカメロン （1-2）\\[中文字幕][Queen Bee]純情デカメロン1.mp4",
        "[230331][nur]ママ喝っ ～乱れ潤うママ友のナカ～.mkv",
        "[230331][ピンクパイナップル]不貞 with ... THE ANIMATION ～人妻ナンパNTR温泉 旅行先でナカよく 種付けされました～.mkv",
        "OVAクラスで男は僕一人！？ ＃1.mkv",
        "GLOD-305.mkv",
        "普通AV-123.mp4",  # 普通AV，用于对比
    ]
    
    for file_path in test_files:
        # 处理路径中的反斜杠
        file_path = file_path.replace('\\', os.sep)
        full_path = os.path.join(test_dir, file_path)
        
        # 创建目录
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # 创建足够大的文件（超过默认的最小文件大小232MiB）
        with open(full_path, 'wb') as f:
            # 写入250MB的数据（250*1024*1024字节）
            f.write(b"0" * 250 * 1024 * 1024)
    
    return test_dir

def test_avid_recognition():
    """测试番号识别"""
    print("=" * 80)
    print("测试动漫番号识别:")
    print("=" * 80)
    
    test_files = [
        "[中文字幕][Queen Bee]純情デカメロン （1-2）\\[中文字幕][Queen Bee]純情デカメロン1.mp4",
        "[230331][nur]ママ喝っ ～乱れ潤うママ友のナカ～.mkv",
        "[230331][ピンクパイナップル]不貞 with ... THE ANIMATION ～人妻ナンパNTR温泉 旅行先でナカよく 種付けされました～.mkv",
        "OVAクラスで男は僕一人！？ ＃1.mkv",
        "GLOD-305.mkv",
        "普通AV-123.mp4",
    ]
    
    for file_path in test_files:
        file_path = file_path.replace('\\', os.sep)
        avid = get_id(file_path)
        av_type = guess_av_type(avid) if avid else "无法识别"
        print(f"文件: {file_path}")
        print(f"  识别结果: {avid}")
        print(f"  类型判断: {av_type}")
        print("-" * 80)

def test_scan_movies():
    """测试扫描影片"""
    print("\n" + "=" * 80)
    print("测试扫描影片:")
    print("=" * 80)
    
    test_dir = create_test_files()
    try:
        movies = scan_movies(test_dir)
        print(f"扫描到 {len(movies)} 部影片:")
        for movie in movies:
            print(f"  番号: {movie.dvdid or movie.cid}, 类型: {movie.data_src}, 文件数: {len(movie.files)}")
    finally:
        # 清理测试目录
        shutil.rmtree(test_dir)
        print(f"\n清理测试目录: {test_dir}")

if __name__ == "__main__":
    print("JavSP 动漫刮削器改进测试")
    print("=" * 80)
    
    test_avid_recognition()
    test_scan_movies()
    
    print("\n" + "=" * 80)
    print("测试完成!")
    print("=" * 80)
