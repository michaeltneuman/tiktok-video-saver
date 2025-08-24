import json
import time
from os import mkdir, chdir, listdir
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import subprocess
import logging
import queue
import threading
import argparse
from tqdm import tqdm

def configure_logging():
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(funcName)s - %(message)s')
    logging.getLogger().setLevel(logging.INFO)

def configure_user_cookies(filename='cookies.json'):
    with open(filename,'r') as _:
        to_return = json.load(_)
    return to_return

def configure_selenium_driver(headless=False):
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("headless")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument('--incognito')
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_experimental_option("prefs", {"profile.managed_default_content_settings.stylesheets": 2})
    return webdriver.Chrome(options=chrome_options)

class SilentLogger:
    def debug(self, msg):
        pass
    def warning(self, msg):
        pass
    def error(self, msg):
        pass

def writer_worker(writer_queue):
    while True:
        liked_video = writer_queue.get()
        with open('urls_downloaded.txt','a+',encoding='utf-8',newline='') as _:
            _.write(liked_video+'\n')
            _.flush()
        logging.info(f"WROTE {liked_video} TO URL FILE")
        writer_queue.task_done()

def mkdir_handle_error(dirname):
    try:
        mkdir(dirname)
    except Exception as e:
        if '[WinError 183] Cannot create a file when that file already exists' not in f"{e}":
            logging.critical(f"{e}")
            exit()
        
def download_worker(downloader_queue,writer_queue,premium_user):
    already_tried = set()
    try:
        with open('urls_downloaded.txt','r',encoding='utf-8') as _:
            already_tried.update(_.read().splitlines())
    except:
        pass
    while True:
        liked_video = downloader_queue.get()
        liked_video,collection_name,slider_photo_data,slider_photo_url,index = liked_video
        if liked_video not in already_tried:
            username, video_id = liked_video.split('https://www.tiktok.com/@')[1].split('/')[0], liked_video.split('/')[-1].strip()
            video_title = f'{username}_VID_{video_id}.mp4'
            if collection_name is not None:
                video_title = f"./{collection_name.replace('/','___')}/" + video_title
            try:
                subprocess.run(['yt-dlp.exe','-f',"best" if premium_user else "worst",'-N','4','--quiet','--no-warnings','-o',video_title,liked_video])
                writer_queue.put(liked_video)
                logging.info(f"{downloader_queue.qsize()} LEFT IN QUEUE || DOWNLOADED VIDEO {username} | {video_id} SUCCESSFULLY")
            except Exception as e:
                logging.error(f"{downloader_queue.qsize()} LEFT IN QUEUE || {liked_video} | {e}")
                downloader_queue.put((liked_video,collection_name,slider_photo_data,slider_photo_url,index))
                logging.info(f"{downloader_queue.qsize()} | NEW VIDEO ADDED {liked_video}")
        downloader_queue.task_done()

def show_qrcode(driver):
    driver.get("""https://www.tiktok.com/login/qrcode""")
    time.sleep(2)
    driver.find_element(By.CSS_SELECTOR, 'div[data-e2e="qr-code"]').screenshot('tiktok_login_qrcode.png')
    

def do_presses(driver,already_found,downloader_queue,writer_queue,download_type,collection_name=None,num_presses=4):
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        logging.info(f"CURRENT HEIGHT {last_height} | COLLECTION {collection_name}")
        for num_presses in range(num_presses):
            driver.find_element(By.TAG_NAME,'body').send_keys(Keys.PAGE_DOWN)
            time.sleep(0.8)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
    logging.info(f"FINAL HEIGHT {last_height}")
    new_vids_added = 0
    page_soup = BeautifulSoup(driver.page_source,'html.parser')
    if download_type == 'liked':
        page_soup = page_soup.find_all('div',{'data-e2e':'user-liked-item'})
    elif download_type == 'collections':
        page_soup = page_soup.find_all('a',{'href':lambda _:_ and _.startswith('https://www.tiktok.com/@')})
    for liked_video in page_soup:
        if download_type == 'liked':
            liked_video = liked_video.find('a')['href']
        elif download_type == 'collections':
            liked_video = liked_video['href']
        if liked_video in already_found:
            continue
        elif '/photo/' in liked_video:
            driver.get(liked_video)
            time.sleep(1.8)
            logging.info(f"START PHOTO SLIDESHOW {liked_video}")
            for index,slider_photo in tqdm(enumerate(BeautifulSoup(driver.page_source,'html.parser').find_all('img',{'src':lambda _:_ and 'photomode-image.jpeg' in _}))):
                driver.get(slider_photo['src'])
                username, video_id = liked_video.split('https://www.tiktok.com/@')[1].split('/')[0], liked_video.split('/')[-1].strip()
                video_title = f'{username}_VID_{video_id}_{str(index).zfill(2)}.png'
                if collection_name is not None:
                    video_title = f"./{collection_name.replace('/','___')}/" + video_title
                driver.save_screenshot(video_title)
            logging.info(f"END PHOTO SLIDESHOW {liked_video}")
            writer_queue.put(liked_video)
        else:
            downloader_queue.put((liked_video,collection_name,None,None,0))
        already_found.add(liked_video)
        new_vids_added += 1
    logging.info(f"{downloader_queue.qsize()} | {new_vids_added} NEW VIDS | {new_height} NEW HEIGHT")
    return driver

def scrolldown(driver,username,download_type='collections',already_found = None,cookies=None,premium_user=True):
    already_found = set()
    try:
        with open('urls_downloaded.txt','r',encoding='utf-8') as _:
            already_found.update(_.read().splitlines())
    except:
        pass
    downloader_queue = queue.Queue()
    writer_queue = queue.Queue()
    for thread_num in range(2):
        vid_download_thread = threading.Thread(target = download_worker, args=(downloader_queue,writer_queue,premium_user))
        vid_download_thread.daemon = True
        vid_download_thread.start()
    for thread_num in range(1):
        writer_thread = threading.Thread(target = writer_worker, args=(writer_queue,))
        writer_thread.daemon = True
        writer_thread.start()
    if download_type=='liked':
        driver.find_element(By.CSS_SELECTOR, 'p[data-e2e="liked-tab"]').click()
        logging.info("CLICKING LIKED TAB")
        time.sleep(1.8)
        driver = do_presses(driver,already_found,downloader_queue,writer_queue,download_type,None,4)
    elif download_type=='collections':
        driver.find_element(By.CSS_SELECTOR, "[class*='-PFavorite']").click()
        logging.info("CLICKING FAVORITE TAB")
        time.sleep(1.8)
        driver.find_element(By.CSS_SELECTOR, "button#collections").click()
        logging.info("CLICKING COLLECTIONS TAB")
        time.sleep(1.8)
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            logging.info(f"GETTING ALL COLLECTIONS || {last_height}")
            for num_presses in range(4):
                driver.find_element(By.TAG_NAME,'body').send_keys(Keys.PAGE_DOWN)
                time.sleep(0.8)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        logging.info(f"ALL COLLECTIONS PARSED, BEGINNING DOWNLOADS")
        time.sleep(1.8)
        page_soup = BeautifulSoup(driver.page_source,'html.parser')
        for collection_index,collection in enumerate(page_soup.find_all('a',{'href':lambda _:_ and _.startswith(f'/@{username}/collection/')})):
            try:
                collection_name = page_soup.find_all('picture')[collection_index].find('img')['alt']
            except:
                continue
            mkdir_handle_error(collection_name.replace('/','___'))
            logging.info(f"MAKING DIRECTORY / CLICKING COLLECTION '{collection_name}'")
            driver.get(f"""https://www.tiktok.com{collection['href']}""")
            time.sleep(2.8)
            driver = do_presses(driver,already_found,downloader_queue,writer_queue,download_type,collection_name,4)
            time.sleep(0.8)
    try:
        driver.quit()
    except:
        pass
    try:
        driver.close()
    except:
        pass
    while True:
        logging.warning(f"END OF PAGE | {downloader_queue.qsize()} DOWNLOADS LEFT | {writer_queue.qsize()} WRITES LEFT")
        time.sleep(5)
        if downloader_queue.qsize()==0 and writer_queue.qsize()==0:
            break
    time.sleep(60)
        

if __name__=='__main__':
    subprocess.run(['yt-dlp.exe','-U'])
    configure_logging()
    parser = argparse.ArgumentParser(description="TikTok Liked Video Downloader")
    parser.add_argument('-u',type=str,help="USERNAME")
    parser.add_argument('-m',type=str,help="TYPE OF DOWNLOAD (options are either ('c') COLLECTIONS or ('l') LIKED VIDEOS",default='c')
    parser.add_argument('-c',type=str,help="COOKIES.JSON_FILEPATH (default= CURRENTDIRECTORY+'cookies.json')",default='cookies.json')
    parser.add_argument('-p',type=int,help="IS PREMIUM USER? IF SO, HIGH QUALITY VIDEOS DOWNLOADED",default=1)
    args = parser.parse_args()
    MY_USERNAME = args.u
    logging.info(f"DOWNLOADING LIKED VIDEOS FOR '@{MY_USERNAME}'")
    cookies = configure_user_cookies(args.c)
    logging.warning(f"LOADED BROWSER COOKIES (if not logged in, won't work!)")
    driver = configure_selenium_driver()
    mkdir_handle_error(MY_USERNAME)
    chdir(MY_USERNAME)
    if args.p==1:
        mkdir_handle_error('PREMIUM')
        chdir('PREMIUM')
    else:
        mkdir_handle_error('FREE')
        chdir('FREE')
    if args.m=='c':
        mkdir_handle_error('Collections')
        chdir('Collections')
    elif args.m=='l':
        mkdir_handle_error('LikedVideos')
        chdir('LikedVideos')
    driver.get(f"https://www.tiktok.com/@{MY_USERNAME}?lang=en")
    for cookie in cookies:
        if "expiry" in cookie:
            cookie["expiry"] = int(cookie["expiry"])
        driver.add_cookie(cookie)
    driver.refresh()
    time.sleep(1.8)
    driver.set_window_position(3000, 0)
    logging.info("COOKIES CONFIGURED")
    scrolldown(driver,MY_USERNAME,'collections' if args.m=='c' else 'liked',cookies=cookies,premium_user=(args.p==1))