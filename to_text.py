import re
import requests
import json
from models import db, Subtitles


def remove_tags(text):
    """
    Remove vtt markup tags
    """
    tags = [
        r'</c>',
        r'<c(\.color\w+)?>',
        r'<\d{2}:\d{2}:\d{2}\.\d{3}>',
    ]

    for pat in tags:
        text = re.sub(pat, '', text)

    # extract timestamp, only kep HH:MM:SS
    text = re.sub(
        r'(\d{2}:\d{2}:\d{2})\.\d{3} --> .* align:start position:0%',
        r'\g<1>',
        text
    )

    text = re.sub(
        r'(\d{2}:\d{2}:\d{2})\.\d{3} --> .*',
        r'\g<1>',
        text
    )

    text = re.sub(r'^\s+$', '', text, flags=re.MULTILINE)
    return text

def remove_header(lines):
    """
    Remove vtt file header
    """
    pos = -1
    for mark in ('##', 'Language: en',):
        if mark in lines:
            pos = lines.index(mark)
    lines = lines[pos+1:]
    return lines

def merge_duplicates(lines):
    """
    Remove duplicated subtitles. Duplacates are always adjacent.
    """
    last_timestamp = ''
    last_cap = ''
    for line in lines:
        if line == "":
            continue
        if re.match(r'^\d{2}:\d{2}:\d{2}$', line):
            if line != last_timestamp:
                yield line
                last_timestamp = line
        else:
            if line != last_cap:
                yield line
                last_cap = line

def merge_short_lines(lines):
    buffer = ''
    for line in lines:
        if line == "" or re.match(r'^\d{2}:\d{2}:\d{2}$', line):
            yield '' + line
            continue

        if len(line+buffer) < 80:
            buffer += ' ' + line
        else:
            yield buffer.strip()
            buffer = line
    yield buffer

def punctuate_online(text):
    API_ENDPOINT = "http://bark.phon.ioc.ee/punctuator"
    data = dict(text=text)
    r = requests.post(url = API_ENDPOINT, data = data)
    punctuatedText = r.text
    return punctuatedText

def duplicate_punctuation(text):
    text = re.sub(r'[\.]+','.',text)
    return text

def convert_to_text(video_id):
    subtitles = Subtitles.query.filter_by(video_id=video_id).first()

    if subtitles.data_text is not None:
        return subtitles.data_text

    vtt_text = subtitles.data_vtt
    vtt_text = remove_tags(vtt_text)
    vtt_lines = vtt_text.splitlines()
    vtt_lines = remove_header(vtt_lines)
    vtt_lines = merge_duplicates(vtt_lines)
    vtt_lines = list(vtt_lines)
    vtt_lines = merge_short_lines(vtt_lines)
    vtt_lines = list(vtt_lines)

    # generate JSON with timestamp and line
    flag = False
    jsonList = []
    counter = 0
    for line in vtt_lines:
        if(re.match(r'^\d{2}:\d{2}:\d{2}$', line) and not flag):
            flag = True
            jsonList.insert(counter,{"time" : line})
        elif not re.match(r'^\d{2}:\d{2}:\d{2}$', line):
            flag = False
            if counter < len(jsonList):
                jsonList[counter]["line"] = line
                counter += 1
            else:
                jsonList[counter - 1]["line"] += ' ' + line


    unPunctuatedText = ''
    for jsonObj in jsonList:
        unPunctuatedText += jsonObj['line'] + ' '

    punctuatedText = punctuate_online(unPunctuatedText)
    punctuatedText = duplicate_punctuation(punctuatedText)

    subtitles.data_text = punctuatedText
    subtitles.data_json = json.dumps(jsonList)

    db.session.add(subtitles)
    db.session.commit()
