from moviepy.editor import AudioFileClip
import logging
import glob


class AudioSplitClient:
    def start(self, path, logger=logging.getLogger()):
        if not path:
            logger.error("音频分离：路径为空！")
            return
        files = glob.glob(path + "/*.mp4")
        if not files:
            logger.error("音频分离：mp4文件未找到")
            return
        for _file in files:
            my_audio_clip = AudioFileClip(_file)
            my_audio_clip.write_audiofile("".join(_file.split(".")[:-1]) + ".wav")
            logger.info(f"{_file}分离音频完成")
        logger.info("音频分离完成")
