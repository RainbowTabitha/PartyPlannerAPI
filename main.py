# ============================================
# Party Planner API
# Author: Nayla Hanegan (naylahanegan@gmail.com)
# Date: 7/21/2024
# License: MIT
# ============================================

from bs4 import BeautifulSoup
from datetime import datetime
from fastapi import FastAPI
from urllib.parse import urlparse, parse_qs, urlsplit, urlunsplit

import re
import requests

app = FastAPI()

def fetch_files(id, file_id=None):
    url = f"https://mariopartylegacy.com/forum/downloads/{id}/history"
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')

    versions = []

    for row in soup.select('.dataList-row'):
        version_info = {}
        
        cells = row.select('.dataList-cell')
        
        if cells:
            version_info["file_version"] = cells[0].get_text(strip=True)
            
            american_date = cells[1].get_text(strip=True)
            try:
                international_date = datetime.strptime(american_date, '%b %d, %Y').strftime('%Y-%m-%d')
            except ValueError:
                international_date = None
            version_info["release_date"] = international_date
            
            version_info["download_count"] = cells[2].get_text(strip=True)
            
            rating_text = cells[3].get_text(strip=True)
            try:
                rating_parts = rating_text.split(' ')
                score = float(rating_parts[0])
                ratings = rating_parts[2]
                stars = score * 0.05 * 400
                formatted_stars = str(int(stars)) if stars.is_integer() else f"{stars:.2f}"
                formatted_rating = f"{formatted_stars}"
            except (IndexError, ValueError):
                formatted_rating = rating_text
            version_info["rating"] = formatted_rating
            
            link = cells[4].select_one('a')
            if link and link['href']:
                version_info["download_link"] = "https://mariopartylegacy.com" + link['href']
                
                path = urlparse(version_info["download_link"]).path
                parts = path.split('/')
                if len(parts) > 3:
                    version_id = parts[3].split('.')[1]
                    version_info["file_id"] = version_id

                try:
                    response_file_name = requests.head("https://mariopartylegacy.com" + link['href'], allow_redirects=True)
                    content_disposition = response_file_name.headers.get('Content-Disposition')
                    if content_disposition:
                        filename = content_disposition.split('filename=')[-1].strip('\"')
                    else:
                        filename = "Filename not found"
                except requests.RequestException:
                    filename = "Filename not found"
                
                version_info["file_name"] = filename
            
            versions.append(version_info)

    # Exclude the first entry
    versions = versions[1:]

    # Filter by file_id if provided
    if file_id:
        versions = [version for version in versions if version.get("file_id") == str(file_id)]

    return versions



def fetch_project(id):
    url = f"https://mariopartylegacy.com/forum/downloads/{id}/"
    response = requests.get(url)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    
    project = []
    project_info = {}  # Initialize project_info dictionary
    
    project_info["id"] = id

    # Extract the h1 element with class 'p-title-value'
    content = soup.find('h1', class_='p-title-value')
    if content:
        title_text = content.text.strip()

        # Remove the prefixes "MP1 ", "MP2 ", "MP3 " and get the remaining text
        for prefix in ["MP1", "MP2", "MP3"]:
            if title_text.startswith(prefix):
                project_info["name"] = title_text[int(len(prefix)+1):]
                project_info["gameId"] = int(title_text[2:int(len(prefix))])
    

    content = soup.find('a', class_='username u-concealed')
    if content:
        title_text = content.text.strip()
        project_info["author"] = title_text
    
    content = soup.find('time', class_='u-dt')
    if content:
        american_date = content.text.strip()
        try:
            international_date = datetime.strptime(american_date, '%b %d, %Y').strftime('%Y-%m-%d')
        except ValueError:
            international_date = None
        project_info["creation_date"] = international_date


    board_difficulty = soup.find('dl', {'data-field': 'board_difficulty'}).find('dd').get_text(strip=True)
    recommended_turns = soup.find('dl', {'data-field': 'board_turns'}).find('dd').get_text(strip=True)
    custom_events = soup.find('dl', {'data-field': 'board_events'}).find('dd').get_text(strip=True)
    custom_music = soup.find('dl', {'data-field': 'board_music'}).find('dd').get_text(strip=True)
    playable_on_n64 = soup.find('dl', {'data-field': 'board_hardware'}).find('dd').get_text(strip=True)
    space_count = soup.find('dl', {'data-field': 'board_spaces'}).find('dd').get_text(strip=True)
    theme = soup.find('dl', {'data-field': 'board_theme'}).find('dd').get_text(strip=True)

    board_difficulty = board_difficulty.replace("Beginner", "1")
    board_difficulty = board_difficulty.replace("Average", "2")
    board_difficulty = board_difficulty.replace("Challenging", "3")
    board_difficulty = board_difficulty.replace("Complex", "4")
    board_difficulty = board_difficulty.replace("Extreme", "5")

    project_info["difficulty"] = int(board_difficulty)
    project_info["recommended_turns"] = int(recommended_turns)

    custom_events = custom_events.replace("No", "0")
    custom_events = custom_events.replace("Yes (Unique)", "2")
    custom_events = custom_events.replace("Yes", "1")
    project_info["custom_events"] = int(custom_events)

    custom_music = custom_music.replace("No", "0")
    custom_music = custom_music.replace("Yes", "1")
    project_info["custom_music"] = int(custom_music)

    playable_on_n64 = playable_on_n64.replace("No", "0")
    playable_on_n64 = playable_on_n64.replace("Yes", "1")
    playable_on_n64 = playable_on_n64.replace("Untested", "2")
    project_info["playable_on_n64"] = int(playable_on_n64)

    project_info["space_count"] = int(space_count)

    project_info["theme"] = theme

    content = soup.find('div', class_='bbWrapper')
    if content:
        title_text = content.text.strip()
        title_text = ' '.join(title_text.splitlines())
        match = re.search(r'(.*?)   Spoiler\s*(.*?)\s*   (.*)', title_text, re.DOTALL)
        if match:
            title_text = match.group(1).strip() + " " + match.group(3).strip()
        project_info["description"] = title_text[3:]

    # Find elements with the classes "contentRow-figure" followed by "avatar avatar--s"
    content_row_figure = soup.find_all('div', class_='contentRow contentRow--hideFigureNarrow')

    for figure in content_row_figure:
        avatar_div = figure.find('span', class_='contentRow-figure')
        if avatar_div:
            img_tag = avatar_div.find('img')
            if img_tag and 'src' in img_tag.attrs:
                project_info_raw = "https://mariopartylegacy.com" + img_tag['src']
                split_url = urlsplit(project_info_raw)
                project_info["icon"] = urlunsplit((split_url.scheme, split_url.netloc, split_url.path, '', ''))

    project.append(project_info)
    
    return project

    

@app.get("/project/{project_id}/")
async def get_project_files(project_id: int):
    project = fetch_project(project_id)
    if project:
        return project[0]
    else:
        return {"error": "Project not found"}, 404

@app.get("/project/{project_id}/files/")
async def get_project_files(project_id: int):
    versions = fetch_files(project_id)
    if versions:
        return {"projectId": project_id, "versions": versions}
    else:
        return {"error": "Project not found"}, 404

@app.get("/project/{project_id}/files/{file_id}")
async def get_project_file(project_id: int, file_id: int):
    versions = fetch_files(project_id, file_id=file_id)
    if versions:
        return versions[0]
    else:
        return {"error": "Project not found"}, 404
    
@app.get("/")
async def root():
    return {"message": "Hello World"}
