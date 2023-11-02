import requests
import json
import os
from datetime import datetime


class VK:
    def __init__(self, vk_access_token, user_link_id, version='5.131'):
        self.token = vk_access_token
        self.id = user_link_id
        self.version = version
        self.params = {'access_token': self.token, 'v': self.version}

    def user_info(self):
        url = 'https://api.vk.com/method/users.get'
        params = {'user_ids': self.id}
        response = requests.get(url, params={**self.params, **params})
        data = response.json()
        if 'response' in data and data['response']:
            user_id = data['response'][0]['id']
            albums = self.get_albums(user_id)
            if albums:
                self.download_photos(user_id, albums)
            return user_id

    def get_albums(self, user_id):
        url = 'https://api.vk.com/method/photos.getAlbums'
        params = {
            'owner_id': user_id,
            'need_system': 1,
            'need_covers': 1
        }
        response = requests.get(url, params={**self.params, **params})
        data = response.json()
        if 'response' in data and 'items' in data['response']:
            albums = data['response']['items']
            for index, album in enumerate(albums, start=1):
                print(f"{index}. Название: {album['title']}, Количество фото: {album['size']}")
            print(f"{len(albums) + 1}. Скачать все альбомы")
            return albums

    def download_photos(self, user_id, albums):
        while True:
            try:
                selected_album = int(input('Введите номер альбома для скачивания фото: '))
                if 1 <= selected_album <= len(albums) + 1:
                    break
                else:
                    print("Пожалуйста, введите правильный номер альбома.")
            except ValueError:
                print("Пожалуйста, введите целое число.")

        if selected_album == len(albums) + 1:
            for album in albums:
                self.download_photos_from_album(user_id, album, album['size'])
        else:
            selected_album -= 1
            album_id = albums[selected_album]['id']
            album_title = albums[selected_album]['title']
            album_size = albums[selected_album]['size']
            while True:
                try:
                    num_photos = input('Введите количество фотографий для сохранения (по умолчанию 5): ')
                    if num_photos == '':
                        num_photos = 5
                        break
                    num_photos = int(num_photos)
                    if 1 <= num_photos <= album_size:
                        break
                    else:
                        print(f"Пожалуйста, введите число от 1 до {album_size}.")
                except ValueError:
                    print("Пожалуйста, введите целое число.")
            self.download_photos_from_album(user_id, {'id': album_id, 'title': album_title, 'size': album_size}, num_photos)

    def download_photos_from_album(self, user_id, album, num_photos):
        data_list = []
        folder_name = f"id{user_id}"
        os.makedirs(folder_name, exist_ok=True)
        folder_path = os.path.join(folder_name, album['title'])
        os.makedirs(folder_path, exist_ok=True)

        url = 'https://api.vk.com/method/photos.get'
        params = {
            'owner_id': user_id,
            'album_id': album['id'],
            'extended': 1,
            'count': num_photos
        }
        response = requests.get(url, params={**self.params, **params})
        data = response.json()
        if 'response' in data and data['response']:
            items = data['response']['items']
            likes_count = {}
            for item in items:
                max_size = max(item['sizes'], key=lambda x: x['width'] * x['height'])
                item_likes = item['likes']['count']
                item_date = datetime.fromtimestamp(item['date']).strftime('%d-%m-%Y %H_%M_%S')
                item_size = max_size['type']  # возможно не правильно понял тз
                item_url = max_size['url']
                file_ext = item_url.split('.')[-1].split('?size')[0]

                if item_likes not in likes_count:
                    likes_count[item_likes] = 0

                date_str = '' if likes_count[item_likes] == 0 else f"_{item_date}"
                filename = f"{folder_path}/{item_likes}{date_str}.{file_ext}"
                with open(filename, 'wb') as file:
                    file.write(requests.get(item_url).content)
                likes_count[item_likes] += 1

                data_dict = {
                    'file_name': filename,
                    'size': item_size
                }
                data_list.append(data_dict)

            users_data = f"{user_id}_{album['title']}_dump.json"
            with open(users_data, 'w') as json_file:
                json.dump(data_list, json_file)


class YaD:
    def __init__(self, token, create_folder_url, upload_url, directory_path):
        self.token = token
        self.create_folder_url = create_folder_url
        self.upload_url = upload_url
        self.directory_path = directory_path

    def get_files_info(self, folder_path):
        files = []
        for root, _, files_list in os.walk(folder_path):
            for file_name in files_list:
                file_path = os.path.join(root, file_name)
                if os.path.isfile(file_path):
                    size = os.path.getsize(file_path)
                    files.append((file_path, size))
        files.sort(key=lambda x: x[1], reverse=True)
        return files

    def create_folder(self, folder_path):
        current_path = ''
        folders = folder_path.split('/')
        for folder in folders:
            current_path += f'/{folder}'
            check_folder_url = f"{self.create_folder_url}/?path={current_path}"
            response = requests.get(check_folder_url, headers={'Authorization': f'OAuth {self.token}'})
            if response.status_code == 404:
                response = requests.put(self.create_folder_url, headers={'Authorization': f'OAuth {self.token}'}, params={'path': current_path})
                if response.status_code not in [201, 409]:
                    print(f"Произошла ошибка при создании папки {current_path} на Яндекс.Диске.")

    def upload_files(self):
        num_photos = 5
        num_photos_input = input('Введите количество фотографий для загрузки на Яндекс.Диск (по умолчанию 5): ')
        if num_photos_input.isdigit():
            num_photos = int(num_photos_input)
        subdirectories = next(os.walk(self.directory_path))[1]
        uploaded_files = []

        for folder in subdirectories:
            folder_path = os.path.join(self.directory_path, folder)
            files = self.get_files_info(folder_path)
            for j, (file, _) in enumerate(files, 1):
                if j > num_photos:
                    break
                with open(file, 'rb') as f:
                    rel_path = os.path.relpath(file, self.directory_path)
                    upload_path = os.path.join(self.directory_path, rel_path)

                    folder_path = os.path.dirname(upload_path)
                    self.create_folder(folder_path)

                    with open(file, 'rb') as f:
                        response = requests.get(self.upload_url, headers={'Authorization': f'OAuth {self.token}'},
                                                params={'path': upload_path, 'overwrite': 'true'})
                        if response.status_code == 200:
                            href = response.json()['href']
                            requests.put(href, data=f)

                    uploaded_files.append(upload_path)

        return uploaded_files

    def logging(self, files_uploaded):
        with open("app.log", "w") as log_file:
            for file in files_uploaded:
                log_file.write(f"Файл {file} успешно загружен на Яндекс.Диск\n")


# VK
access_token = ''
profile_link = input('Введите id или ссылку на профиль пользователя ВКонтакте: ')
user_link_id = profile_link.rsplit('/', 1)[-1]
vk = VK(access_token, user_link_id)
user_id = vk.user_info()

# Инициализация YaD
token = ''
create_folder_url = 'https://cloud-api.yandex.net/v1/disk/resources'
upload_url = 'https://cloud-api.yandex.net/v1/disk/resources/upload'
directory_path = f'id{user_id}'
yad = YaD(token, create_folder_url, upload_url, directory_path)

# # Использование объекта YaD
files = yad.get_files_info(directory_path)
print(f"В директории {directory_path} находится {len(files)} файлов.")
files_uploaded = yad.upload_files()
yad.logging(files_uploaded)