import youtube_dl
import os
from models import Subtitles, db


def get_vtt_file(video_id):
    subtitles = Subtitles.query.filter_by(video_id=video_id).first()
    if subtitles is not None:
        return
    static = os.path.join(os.path.curdir, "static")
    vtt_folder = os.path.join(static, "vtt")
    vtt_file_path = os.path.join(vtt_folder, video_id)
    ydl_opts = {
    'skip_download': True,
    'subtitlesformat': 'vtt',
    'writeautomaticsub': True,
    'outtmpl': vtt_file_path + '.%(ext)s',
    }

    url = 'https://www.youtube.com/watch?v=' + video_id

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    vtt_file_path = str(vtt_file_path) + '.en.vtt'
    with open(vtt_file_path) as f:
        text = f.read()

    subtitles = Subtitles(
        video_id = video_id,
        data_vtt = text
    )
    db.session.add(subtitles)
    db.session.commit()
