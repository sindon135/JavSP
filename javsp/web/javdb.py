"""从JavDB抓取数据"""
import os
import re
import logging

from javsp.web.base import Request, resp2html
from javsp.web.exceptions import *
from javsp.func import *
from javsp.avid import guess_av_type
from javsp.config import Cfg, CrawlerID
from javsp.datatype import MovieInfo, GenreMap
from javsp.chromium import get_browsers_cookies


# 初始化Request实例。使用scraper绕过CloudFlare后，需要指定网页语言，否则可能会返回其他语言网页，影响解析
request = Request(use_scraper=True)
request.headers['Accept-Language'] = 'zh-CN,zh;q=0.9,zh-TW;q=0.8,en-US;q=0.7,en;q=0.6,ja;q=0.5'

logger = logging.getLogger(__name__)
genre_map = GenreMap('data/genre_javdb.csv')
permanent_url = 'https://javdb.com'
if Cfg().network.proxy_server is not None:
    base_url = permanent_url
else:
    base_url = str(Cfg().network.proxy_free[CrawlerID.javdb])


def get_html_wrapper(url):
    """包装外发的request请求并负责转换为可xpath的html，同时处理Cookies无效等问题"""
    global request, cookies_pool
    r = request.get(url, delay_raise=True)
    if r.status_code == 200:
        # 发生重定向可能仅仅是域名重定向，因此还要检查url以判断是否被跳转到了登录页
        if r.history and '/login' in r.url:
            # 仅在需要时去读取Cookies
            if 'cookies_pool' not in globals():
                try:
                    cookies_pool = get_browsers_cookies()
                except (PermissionError, OSError) as e:
                    logger.warning(f"无法从浏览器Cookies文件获取JavDB的登录凭据({e})，可能是安全软件在保护浏览器Cookies文件", exc_info=True)
                    cookies_pool = []
                except Exception as e:
                    logger.warning(f"获取JavDB的登录凭据时出错({e})，你可能使用的是国内定制版等非官方Chrome系浏览器", exc_info=True)
                    cookies_pool = []
            if len(cookies_pool) > 0:
                item = cookies_pool.pop()
                # 更换Cookies时需要创建新的request实例，否则cloudscraper会保留它内部第一次发起网络访问时获得的Cookies
                request = Request(use_scraper=True)
                request.cookies = item['cookies']
                cookies_source = (item['profile'], item['site'])
                logger.debug(f'未携带有效Cookies而发生重定向，尝试更换Cookies为: {cookies_source}')
                return get_html_wrapper(url)
            else:
                raise CredentialError('JavDB: 所有浏览器Cookies均已过期')
        elif r.history and 'pay' in r.url.split('/')[-1]:
            raise SitePermissionError(f"JavDB: 此资源被限制为仅VIP可见: '{r.history[0].url}'")
        else:
            html = resp2html(r)
            return html
    elif r.status_code in (403, 503):
        html = resp2html(r)
        code_tag = html.xpath("//span[@class='code-label']/span")
        error_code = code_tag[0].text if code_tag else None
        if error_code:
            if error_code == '1020':
                block_msg = f'JavDB: {r.status_code} 禁止访问: 站点屏蔽了来自日本地区的IP地址，请使用其他地区的代理服务器'
            else:
                block_msg = f'JavDB: {r.status_code} 禁止访问: {url} (Error code: {error_code})'
        else:
            block_msg = f'JavDB: {r.status_code} 禁止访问: {url}'
        raise SiteBlocked(block_msg)
    else:
        raise WebsiteError(f'JavDB: {r.status_code} 非预期状态码: {url}')


def get_user_info(site, cookies):
    """获取cookies对应的JavDB用户信息"""
    try:
        request.cookies = cookies
        html = request.get_html(f'https://{site}/users/profile')
    except Exception as e:
        logger.info('JavDB: 获取用户信息时出错')
        logger.debug(e, exc_info=1)
        return
    # 扫描浏览器得到的Cookies对应的临时域名可能会过期，因此需要先判断域名是否仍然指向JavDB的站点
    if 'JavDB' in html.text:
        email = html.xpath("//div[@class='user-profile']/ul/li[1]/span/following-sibling::text()")[0].strip()
        username = html.xpath("//div[@class='user-profile']/ul/li[2]/span/following-sibling::text()")[0].strip()
        return email, username
    else:
        logger.debug('JavDB: 域名已过期: ' + site)


def get_valid_cookies():
    """扫描浏览器，获取一个可用的Cookies"""
    # 经测试，Cookies所发往的域名不需要和登录时的域名保持一致，只要Cookies有效即可在多个域名间使用
    for d in cookies_pool:
        info = get_user_info(d['site'], d['cookies'])
        if info:
            return d['cookies']
        else:
            logger.debug(f"{d['profile']}, {d['site']}: Cookies无效")


def parse_data(movie: MovieInfo):
    """从网页抓取并解析指定番号的数据
    Args:
        movie (MovieInfo): 要解析的影片信息，解析后的信息直接更新到此变量内
    """
    # 处理特殊格式的番号
    original_dvdid = movie.dvdid
    
    # 如果是WESTERN:前缀，移除前缀并提取搜索关键词
    if original_dvdid.upper().startswith('WESTERN:'):
        western_id = original_dvdid[8:]  # 移除'WESTERN:'前缀
        # 提取系列名和标题关键词
        # 格式：系列.日期.演员.标题 或 系列.日期.标题
        parts = western_id.split('.')
        if len(parts) >= 2:
            # 提取系列名（第一个部分）
            series_name = parts[0]
            # 提取标题关键词（最后几个部分）
            title_keywords = parts[-2:] if len(parts) >= 3 else parts[-1:]
            # 构建搜索关键词
            search_query = f"{series_name} {' '.join(title_keywords)}"
        else:
            search_query = western_id
        logger.debug(f"欧美番号搜索: '{original_dvdid}' -> 关键词: '{search_query}'")
        html = get_html_wrapper(f'{base_url}/search?q={search_query}')
    
    # 如果是ANIME:前缀，提取标题进行搜索
    elif original_dvdid.upper().startswith('ANIME:'):
        # 移除'ANIME:'前缀，提取标题
        # 格式可能是: ANIME:标题 或 ANIME:厂商:标题
        anime_parts = original_dvdid.split(':', 2)
        if len(anime_parts) >= 3:
            # ANIME:厂商:标题
            title = anime_parts[2]
        else:
            # ANIME:标题
            title = original_dvdid[6:]  # 移除'ANIME:'前缀
        
        # 清理标题：移除可能的分片标识（CD1, CD2等）
        # 这些已经在avid.py中处理过，但这里再处理一次以确保安全
        clean_title = re.sub(r'[-_\s]*(CD|Part|PART|DISC|DISK|DVD|BD|DISK|DISC)[-__\s]*\d+', '', title, flags=re.IGNORECASE)
        clean_title = re.sub(r'[-_\s]*\d+$', '', clean_title)  # 移除末尾的数字
        clean_title = clean_title.strip()
        
        search_query = clean_title[:50]  # 限制搜索长度
        logger.debug(f"动漫番号搜索: '{original_dvdid}' -> 清理后标题: '{clean_title}' -> 关键词: '{search_query}'")
        html = get_html_wrapper(f'{base_url}/search?q={search_query}')
    
    else:
        # 普通番号搜索
        html = get_html_wrapper(f'{base_url}/search?q={movie.dvdid}')
    
    ids = list(map(str.lower, html.xpath("//div[@class='video-title']/strong/text()")))
    movie_urls = html.xpath("//a[@class='box']/@href")
    
    # 首先尝试完全匹配
    match_count = len([i for i in ids if i == movie.dvdid.lower()])
    index = None
    new_url = None
    
    # 对于动漫文件，如果搜索的是ANIME:前缀，检查搜索结果中的标题是否匹配
    if match_count == 0 and movie.dvdid.upper().startswith('ANIME:'):
        # 提取搜索标题（移除ANIME:前缀）
        search_title = movie.dvdid[6:]  # 移除'ANIME:'前缀
        
        # 在搜索结果页面中查找标题
        # 搜索结果中的标题通常在<div class="video-title">的<span>或直接文本中
        # 但我们需要获取每个结果的详细信息来检查标题
        # 作为简化方案，我们检查搜索结果中的番号对应的标题是否包含搜索关键词
        # 首先获取所有搜索结果的标题
        result_titles = html.xpath("//div[@class='video-title']/span/text()")
        if not result_titles:
            # 如果没有span，尝试获取strong后面的文本
            result_titles = []
            for title_div in html.xpath("//div[@class='video-title']"):
                # 获取strong元素后面的所有文本
                strong_text = title_div.xpath("strong/text()")
                if strong_text:
                    # 获取strong后面的文本
                    following_text = title_div.xpath("text()")
                    if following_text:
                        result_titles.append(following_text[0].strip())
        
        logger.debug(f"动漫文件搜索: '{search_title}'，找到{len(result_titles)}个标题")
        
        # 检查每个结果的标题是否包含搜索标题
        for i, result_title in enumerate(result_titles):
            if result_title and search_title in result_title:
                match_count = 1
                index = i
                new_url = movie_urls[i]
                # 更新番号为实际的番号（如JDXA-57665）
                actual_id = ids[i]
                movie.dvdid = actual_id
                logger.debug(f"动漫标题匹配成功: '{search_title}' -> '{result_title}' (ID: {actual_id})")
                break
        
        # 如果标题匹配失败，尝试检查番号是否在动漫前缀列表中
        if match_count == 0:
            for i, result_id in enumerate(ids):
                # 检查番号是否是动漫番号
                if guess_av_type(result_id) == 'anime':
                    match_count = 1
                    index = i
                    new_url = movie_urls[i]
                    logger.debug(f"动漫番号匹配: '{search_title}' -> 动漫番号 '{result_id}'")
                    break
    
    # 如果完全匹配失败，尝试模糊匹配（特别是对欧美番号）
    if match_count == 0:
        # 预处理番号用于模糊匹配
        def normalize_for_match(text):
            """预处理文本用于模糊匹配"""
            # 将点号替换为空格（处理欧美番号格式）
            text = re.sub(r'[._]', ' ', text.lower())
            # 移除多余空格
            text = re.sub(r'\s+', ' ', text).strip()
            
            # 对于欧美番号，尝试提取关键部分
            # 常见格式：系列.日期.标题 或 系列.标题
            parts = text.split()
            
            # 如果包含日期格式（如25.11.18），移除日期部分
            # 日期通常由数字组成，可能有2-3组数字
            filtered_parts = []
            for part in parts:
                # 检查是否为日期格式（纯数字，可能包含点号但已经被替换为空格）
                if re.match(r'^\d{1,2}\s\d{1,2}\s\d{1,2}$', part.replace(' ', '')):
                    continue  # 跳过日期部分
                if re.match(r'^\d+$', part):
                    continue  # 跳过纯数字
                filtered_parts.append(part)
            
            if filtered_parts:
                text = ' '.join(filtered_parts)
            
            # 移除所有空格用于比较（因为JavDB搜索结果可能包含空格）
            text_no_spaces = text.replace(' ', '')
            
            return text_no_spaces
        
        avid_normalized = normalize_for_match(movie.dvdid)
        
        # 尝试在搜索结果中查找匹配项
        for i, result_id in enumerate(ids):
            result_normalized = normalize_for_match(result_id)
            
            # 检查是否匹配
            if (avid_normalized == result_normalized or
                avid_normalized in result_normalized or
                result_normalized in avid_normalized):
                match_count = 1
                index = i
                new_url = movie_urls[i]
                logger.debug(f"模糊匹配成功: '{movie.dvdid}' -> '{result_id}'")
                break
        
        # 如果还是没找到，检查是否可能是欧美番号（包含点号）
        if match_count == 0 and '.' in movie.dvdid:
            # 对于欧美番号，尝试更智能的搜索策略
            # 格式通常是：系列.日期.演员.标题 或 系列.日期.标题
            # 最佳搜索策略：系列 + 标题关键词
            
            # 1. 提取系列名（第一个点号前的部分）
            series_match = re.match(r'^([a-z]+)\.', movie.dvdid.lower())
            if series_match:
                series_name = series_match.group(1)
                
                # 2. 提取标题关键词（移除系列名、日期、常见演员名）
                # 先移除系列名和日期
                title_part = re.sub(r'^[a-z]+\.\d{1,2}\.\d{1,2}\.\d{1,2}\.', '', movie.dvdid.lower())
                title_part = re.sub(r'^[a-z]+\.\d{1,2}\.\d{1,2}\.', '', title_part)
                
                # 移除常见的演员名（这里可以扩展）
                common_actors = ['zoey', 'chloe', 'mia', 'lily', 'sophie', 'emma', 'ava', 'olivia']
                for actor in common_actors:
                    title_part = re.sub(r'\b' + actor + r'\b\.?', '', title_part)
                
                # 清理多余点号
                title_part = re.sub(r'\.+', '.', title_part).strip('.')
                
                # 3. 构建搜索关键词：系列 + 标题关键词
                if title_part:
                    search_keywords = f"{series_name} {title_part}"
                else:
                    search_keywords = series_name
                
                logger.debug(f"欧美番号智能搜索: '{movie.dvdid}' -> 关键词: '{search_keywords}'")
                
                # 在结果中查找匹配
                for i, result_id in enumerate(ids):
                    result_lower = result_id.lower()
                    # 检查是否包含系列名
                    if series_name in result_lower:
                        # 如果有关键词，检查是否也包含关键词
                        if title_part:
                            # 将标题部分按点号分割成关键词
                            title_keywords = [kw for kw in title_part.split('.') if kw]
                            # 检查是否至少匹配一个关键词
                            for kw in title_keywords:
                                if kw in result_lower:
                                    match_count = 1
                                    index = i
                                    new_url = movie_urls[i]
                                    logger.debug(f"欧美番号关键词匹配: '{movie.dvdid}' -> '{result_id}' (关键词: {kw})")
                                    break
                            if match_count == 1:
                                break
                        else:
                            # 只有系列名，直接匹配
                            match_count = 1
                            index = i
                            new_url = movie_urls[i]
                            logger.debug(f"欧美番号系列匹配: '{movie.dvdid}' -> '{result_id}'")
                            break
    
    # 如果匹配失败，抛出异常
    if match_count == 0:
        raise MovieNotFoundError(__name__, movie.dvdid, ids)
    elif match_count == 1:
        # 如果index为None，说明是完全匹配
        if index is None:
            index = ids.index(movie.dvdid.lower())
            new_url = movie_urls[index]
        
        try:
            html2 = get_html_wrapper(new_url)
        except (SitePermissionError, CredentialError):
            # 不开VIP不让看，决定榨出能获得的信息
            box = html.xpath("//a[@class='box']")[index]
            movie.url = new_url
            movie.title = box.get('title')
            movie.cover = box.xpath("div/img/@src")[0]
            score_str = box.xpath("div[@class='score']/span/span")[0].tail
            score = re.search(r'([\d.]+)分', score_str).group(1)
            movie.score = "{:.2f}".format(float(score)*2)
            movie.publish_date = box.xpath("div[@class='meta']/text()")[0].strip()
            return
    else:
        raise MovieDuplicateError(__name__, movie.dvdid, match_count)

    container = html2.xpath("/html/body/section/div/div[@class='video-detail']")[0]
    info = container.xpath("//nav[@class='panel movie-panel-info']")[0]
    title = container.xpath("h2/strong[@class='current-title']/text()")[0]
    show_orig_title = container.xpath("//a[contains(@class, 'meta-link') and not(contains(@style, 'display: none'))]")
    if show_orig_title:
        movie.ori_title = container.xpath("h2/span[@class='origin-title']/text()")[0]
    cover = container.xpath("//img[@class='video-cover']/@src")[0]
    preview_pics = container.xpath("//a[@class='tile-item'][@data-fancybox='gallery']/@href")
    preview_video_tag = container.xpath("//video[@id='preview-video']/source/@src")
    if preview_video_tag:
        preview_video = preview_video_tag[0]
        if preview_video.startswith('//'):
            preview_video = 'https:' + preview_video
        movie.preview_video = preview_video
    dvdid = info.xpath("div/span")[0].text_content()
    publish_date = info.xpath("div/strong[text()='日期:']")[0].getnext().text
    duration = info.xpath("div/strong[text()='時長:']")[0].getnext().text.replace('分鍾', '').strip()
    director_tag = info.xpath("div/strong[text()='導演:']")
    if director_tag:
        movie.director = director_tag[0].getnext().text_content().strip()
    av_type = guess_av_type(movie.dvdid)
    if av_type != 'fc2':
        producer_tag = info.xpath("div/strong[text()='片商:']")
    else:
        producer_tag = info.xpath("div/strong[text()='賣家:']")
    if producer_tag:
        movie.producer = producer_tag[0].getnext().text_content().strip()
    publisher_tag = info.xpath("div/strong[text()='發行:']")
    if publisher_tag:
        movie.publisher = publisher_tag[0].getnext().text_content().strip()
    serial_tag = info.xpath("div/strong[text()='系列:']")
    if serial_tag:
        movie.serial = serial_tag[0].getnext().text_content().strip()
    score_tag = info.xpath("//span[@class='score-stars']")
    if score_tag:
        score_str = score_tag[0].tail
        score = re.search(r'([\d.]+)分', score_str).group(1)
        movie.score = "{:.2f}".format(float(score)*2)
    genre_tags = info.xpath("//strong[text()='類別:']/../span/a")
    genre, genre_id = [], []
    for tag in genre_tags:
        pre_id = tag.get('href').split('/')[-1]
        genre.append(tag.text)
        genre_id.append(pre_id)
        # 判定影片有码/无码
        subsite = pre_id.split('?')[0]
        movie.uncensored = {'uncensored': True, 'tags':False}.get(subsite)
    # JavDB目前同时提供男女优信息，根据用来标识性别的符号筛选出女优
    actors_tag = info.xpath("//strong[text()='演員:']/../span")[0]
    all_actors = actors_tag.xpath("a/text()")
    genders = actors_tag.xpath("strong/text()")
    actress = [i for i in all_actors if genders[all_actors.index(i)] == '♀']
    magnet = container.xpath("//div[@class='magnet-name column is-four-fifths']/a/@href")

    movie.dvdid = dvdid
    # 移除base_url的尾部斜杠以确保正确替换
    base_url_normalized = base_url.rstrip('/')
    movie.url = new_url.replace(base_url_normalized, permanent_url)
    movie.title = title.replace(dvdid, '').strip()
    movie.cover = cover
    movie.preview_pics = preview_pics
    movie.publish_date = publish_date
    movie.duration = duration
    movie.genre = genre
    movie.genre_id = genre_id
    movie.actress = actress
    movie.magnet = [i.replace('[javdb.com]','') for i in magnet]


def parse_clean_data(movie: MovieInfo):
    """解析指定番号的影片数据并进行清洗"""
    try:
        parse_data(movie)
        # 检查封面URL是否真的存在对应图片
        if movie.cover is not None:
            r = request.head(movie.cover)
            if r.status_code != 200:
                movie.cover = None
    except SiteBlocked:
        raise
        logger.error('JavDB: 可能触发了反爬虫机制，请稍后再试')
    if movie.genre_id and (not movie.genre_id[0].startswith('fc2?')):
        movie.genre_norm = genre_map.map(movie.genre_id)
        movie.genre_id = None   # 没有别的地方需要再用到，清空genre id（表明已经完成转换）


def collect_actress_alias(type=0, use_original=True):
    """
    收集女优的别名
    type: 0-有码, 1-无码, 2-欧美
    use_original: 是否使用原名而非译名，True-田中レモン，False-田中檸檬
    """
    import json
    import time
    import random

    actressAliasMap = {}

    actressAliasFilePath = "data/actress_alias.json"
    # 检查文件是否存在
    if not os.path.exists(actressAliasFilePath):
        # 如果文件不存在，创建文件并写入空字典
        with open(actressAliasFilePath, "w", encoding="utf-8") as file:
            json.dump({}, file)

    typeList = ["censored", "uncensored", "western"]
    page_url = f"{base_url}/actors/{typeList[type]}"
    while True:
        try:
            html = get_html_wrapper(page_url)
            actors = html.xpath("//div[@class='box actor-box']/a")

            count = 0
            for actor in actors:
                count += 1
                actor_name = actor.xpath("strong/text()")[0].strip()
                actor_url = actor.xpath("@href")[0]
                # actor_url = f"https://javdb.com{actor_url}"  # 构造演员主页的完整URL

                # 进入演员主页，获取更多信息
                actor_html = get_html_wrapper(actor_url)
                # 解析演员所有名字信息
                names_span = actor_html.xpath("//span[@class='actor-section-name']")[0]
                aliases_span_list = actor_html.xpath("//span[@class='section-meta']")
                aliases_span = aliases_span_list[0]

                names_list = [name.strip() for name in names_span.text.split(",")]
                if len(aliases_span_list) > 1:
                    aliases_list = [
                        alias.strip() for alias in aliases_span.text.split(",")
                    ]
                else:
                    aliases_list = []

                # 将信息添加到actressAliasMap中
                actressAliasMap[names_list[-1 if use_original else 0]] = (
                    names_list + aliases_list
                )
                print(
                    f"{count} --- {names_list[-1 if use_original else 0]}: {names_list + aliases_list}"
                )

                if count == 10:
                    # 将数据写回文件
                    with open(actressAliasFilePath, "r", encoding="utf-8") as file:
                        existing_data = json.load(file)

                    # 合并现有数据和新爬取的数据
                    existing_data.update(actressAliasMap)

                    # 将合并后的数据写回文件
                    with open(actressAliasFilePath, "w", encoding="utf-8") as file:
                        json.dump(existing_data, file, ensure_ascii=False, indent=2)

                    actressAliasMap = {}  # 重置actressAliasMap

                    print(
                        f"已爬取 {count} 个女优，数据已更新并写回文件:",
                        actressAliasFilePath,
                    )

                    # 重置计数器
                    count = 0

                time.sleep(max(1, 10 * random.random()))  # 随机等待 1-10 秒

            # 判断是否有下一页按钮
            next_page_link = html.xpath(
                "//a[@rel='next' and @class='pagination-next']/@href"
            )
            if not next_page_link:
                break  # 没有下一页，结束循环
            else:
                next_page_url = f"{next_page_link[0]}"
                page_url = next_page_url

        except SiteBlocked:
            raise

    with open(actressAliasFilePath, "r", encoding="utf-8") as file:
        existing_data = json.load(file)

    # 合并现有数据和新爬取的数据
    existing_data.update(actressAliasMap)

    # 将合并后的数据写回文件
    with open(actressAliasFilePath, "w", encoding="utf-8") as file:
        json.dump(existing_data, file, ensure_ascii=False, indent=2)

    print(f"已爬取 {count} 个女优，数据已更新并写回文件:", actressAliasFilePath)


if __name__ == "__main__":
    # collect_actress_alias()
    movie = MovieInfo('FC2-2735981')
    try:
        parse_clean_data(movie)
        print(movie)
    except CrawlerError as e:
        print(repr(e))
