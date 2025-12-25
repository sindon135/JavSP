import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from javsp.avid import get_id, guess_av_type

# 测试动漫文件名
test_files = [
    "[中文字幕][Queen Bee]純情デカメロン （1-2）\\[中文字幕][Queen Bee]純情デカメロン1.mp4",
    "[荻原沙优][230728][ショーテン]種付おじさんとNTR人妻セックス The Animation 1920x1080\\[荻原沙优][230728][ショーテ ン]種付おじさんとNTR人妻セックス The Animation 1920x1080.mp4",
    "[230331][nur]ママ喝っ ～乱れ潤うママ友のナカ～.mkv",
    "[230331][ピンクパイナップル]不貞 with ... THE ANIMATION ～人妻ナンパNTR温泉 旅行先でナカよく 種付けされました～.mkv",
    "[230331][魔人]おとぎばなしの鬼ごっこ 第二話 アリスの壊れた世界.mkv",
    "[230317][メリー・ジェーン]思春期のお勉強 第4話デートをしてみたいお年頃.mkv",
    "[230331][ショーテン]いくものがかり The Animation 上巻.mkv",
    "[230331][魔人]ゴブリンの巣穴 第一話 巡礼者 アンヴィル.mkv",
    "[一天打五吨发蜡]この恋に気づいて THE ANIMATION(No 1920x1080\\[荻原沙优]この恋に気づいて THE ANIMATION(No 1920x1080.mp4",
    "OVAクラスで男は僕一人！？ ＃1.mkv",
    "OVA母乳ちゃんは射したい。＃1.mkv",
    "GLOD-305.mkv",
    "HUNTB-123.mkv",
    "ANIM-456.mkv",
]

print("测试动漫番号识别:")
print("=" * 80)

for filepath in test_files:
    avid = get_id(filepath)
    av_type = guess_av_type(avid) if avid else "无法识别"
    print(f"文件: {filepath[:60]}...")
    print(f"  识别结果: {avid}")
    print(f"  类型判断: {av_type}")
    print("-" * 80)
