# tiktok-video-saver
Download your TikTok videos from your Collections and Liked video tabs using selenium

**Required files in directory**
1. ChromeDriver (chromedriver.exe) - https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json
2. FFMpeg (ffprobe.exe, ffplay.exe, ffmpeg.exe) - https://www.gyan.dev/ffmpeg/builds/
3. yt-dlp (yt-dlp.exe) - https://github.com/yt-dlp/yt-dlp
4. cookies.json - A JSON representation of cookies where you are **authenticated to TikTok on the account whose videos you are downloading!**

**How to run the script**
1. Download a JSON version of your cookies after authenticating to TikTok as "cookies.json" for Selenium to be able to handle locally
2. After putting the required 6 files (chromedriver.exe, ffprobe.exe, ffplay.exe, ffmpeg.exe, yt-dlp.exe, cookies.json) in the same directory as the script (tiktok-likes.py), run the following command
**python tiktok-likes.py -u YOUR_USERNAME**
