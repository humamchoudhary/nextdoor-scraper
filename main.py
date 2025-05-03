import random
from pprint import pprint
from selenium.common.exceptions import NoSuchElementException
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv
import os
import time
from yaspin import yaspin
# from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
import requests
from urllib.parse import urlparse
import os
import tempfile

# Load environment variables from .env file
load_dotenv()
USERNAME = os.getenv("username")
PASSWORD = os.getenv("password")

# Set up Chrome driver
options = Options()
# remove this line if you want to see the browser
options.add_argument("--headless")

options.add_argument("--disable-infobars")
options.add_argument("--disable-extensions")
options.add_argument("--disable-popup-blocking")
options.add_experimental_option("useAutomationExtension", False)
options.add_experimental_option("excludeSwitches", ['enable-automation'])

ua = UserAgent()
user_agent = ua.random

options.add_argument(f"user-agent={user_agent}")
driver = webdriver.Chrome(service=ChromeService(), options=options)

# Replace with your target URL


with yaspin(text="Logging In ", color="blue", side='right') as spinner:
    login_url = "https://nextdoor.com/login/"
    driver.get(login_url)

    time.sleep(2)

    username_field = driver.find_element(By.NAME, "email")
    password_field = driver.find_element(By.NAME, "password")

    username_field.send_keys(USERNAME)
    password_field.send_keys(PASSWORD)
    password_field.send_keys(Keys.RETURN)

    while True:
        if driver.current_url != login_url:
            break
        time.sleep(0.3)


def download_image(url, folder='./tmp'):
    """Download an image from a URL and return the local file path"""
    if not os.path.exists(folder):
        os.makedirs(folder)

    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        # Extract filename from URL or generate one
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path) or 'downloaded_image.jpg'
        filepath = os.path.join(folder, filename) + ".png"

        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)

        return filepath
    except Exception as e:
        print(f"Error downloading image: {e}")
        return None


def extract_feed_item_info(soup):

    # Extract first and last name
    name_element = soup.find(
        'span', class_='Styled_color-sm__zpop7k3', string=True)
    full_name = name_element.get_text(strip=True) if name_element else ""

    # Extract city
    city_element = soup.find('a', class_='post-byline-redesign')
    city = city_element.get_text(strip=True) if city_element else ""

    # Extract review text
    review_element = soup.find('span', class_='Linkify')
    review = review_element.get_text(strip=True) if review_element else ""

    # Extract image (avatar fallback)
    image_element = soup.find('div', {'data-testid': 'avatar'}).find('img')
    # print(image_element)

    # image_url = image_element.find("img").src if image_element else None
    image_url = image_element['src'] if image_element and image_element.has_attr(
        'src') else None

    return {
        'full_name': full_name,
        'city': city,
        'review': review.replace("\n", ""),
        'image_url': image_url
    }


def upload_image_from_data(data_item, upload_input, fallback_folder='images'):
    """Upload image from data if available, otherwise use random image from fallback folder"""
    # Try to use image_url from data if available
    if data_item.get('image_url'):
        try:
            # Download the image to temp folder
            temp_dir = './tmp'
            image_path = download_image(data_item['image_url'], temp_dir)

            if image_path:
                # Upload the downloaded image
                upload_input.send_keys(os.path.abspath(image_path))

                # Delete the temporary file after upload
                try:
                    os.remove(image_path)
                except Exception as e:
                    print(f"Error deleting temporary file: {e}")

                return os.path.basename(image_path)
        except Exception as e:
            print(f"Error processing data image: {
                  e}. Falling back to random image.")

    # Fall back to random image from folder
    return upload_random_image(fallback_folder, upload_input)


def upload_random_image(image_folder, upload_input):
    """Original function for fallback random image selection"""
    # Get list of images from library folder
    image_files = [f for f in os.listdir(
        image_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    if not image_files:
        raise ValueError("No images found in the specified folder")

    # Select random image
    selected_image = random.choice(image_files)
    image_path = os.path.join(image_folder, selected_image)

    # Upload the image
    upload_input.send_keys(os.path.abspath(image_path))

    return selected_image


with yaspin(text="Extracting Reviews ", color="blue", side='right') as spinner:

    post_page = 'https://nextdoor.com/pages/luke-tree-service-seattle-wa/?init_source=search'
    driver.get(post_page)
    time.sleep(10)
    while True:
        try:
            elm = EC.element_to_be_clickable(
                (By.CSS_SELECTOR, '[data-testid="see-more-recommendations-button"]'))
            if elm:
                button = driver.find_element(
                    By.CSS_SELECTOR, '[data-testid="see-more-recommendations-button"]')
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", button)
                time.sleep(1)
                button.click()
                time.sleep(2)

        except NoSuchElementException:
            break

        except:
            pass

    rec_section = driver.find_element(By.ID, "recommendations-section")
    html_fragment = rec_section.get_attribute("outerHTML")
    soup = BeautifulSoup(html_fragment, "html.parser").find('div')
    # soup = BeautifulSoup(str(soup.prettify()), "html.parser")
    elements = soup.find_all(attrs={"data-testid": "feed-item-card"})
    data = []

    for el in elements:
        data.append(extract_feed_item_info(el))


# print(data)


def get_data_subset(data):
    """Returns a subset of data based on user input for range or specific indices."""
    for i in range(len(data)):
        print(f" [{i}] - {data[i]["full_name"]}")
    print(f"\nTotal items: {len(data)}")
    print("Enter either:")
    print("- A range (e.g., '2-5')")
    print("- Specific indices (e.g., '1,3,5')")
    print("- 'all' for everything")

    while True:
        user_input = input("\nYour selection: ").strip()

        if user_input.lower() == 'all':
            return data

        # Handle range input (e.g., "2-5")
        if '-' in user_input:
            try:
                start, end = map(int, user_input.split('-'))
                if start < 0 or end >= len(data):
                    print(f"Error: Indices must be between 0 and {
                          len(data)-1}")
                    continue
                return data[start:end+1]
            except ValueError:
                print("Invalid range format. Use 'start-end' (e.g., '2-5')")

        # Handle specific indices (e.g., "1,3,5")
        elif ',' in user_input:
            try:
                indices = [int(i.strip()) for i in user_input.split(',')]
                if any(i < 0 or i >= len(data) for i in indices):
                    print(f"Error: All indices must be between 0 and {
                          len(data)-1}")
                    continue
                return [data[i] for i in indices]
            except ValueError:
                print(
                    "Invalid indices format. Use comma-separated numbers (e.g., '1,3,5')")

        # Handle single index
        else:
            try:
                index = int(user_input)
                if index < 0 or index >= len(data):
                    print(f"Error: Index must be between 0 and {len(data)-1}")
                    continue
                return [data[index]]
            except ValueError:
                print("Invalid input. Please enter a range, indices, or 'all'")


while True:
    data_temp = get_data_subset(data)
    print("Selected data: ")
    for d in data_temp:
        print(d['full_name'])

    x = input("Confirm [y/n]: ")
    if x.lower() == "y":
        data = data_temp
        del data_temp
        break

# pprint(data)


def send_input(elmn, text):
    elmn.send_keys(text)


for d in data:
    with yaspin(text=f"Uploading Review: {d["full_name"]} ", color="blue", side='right') as spinner:

        review_url = "https://luketreeservice.com/review"
        driver.get(review_url)
        time.sleep(2)
        inps = driver.find_elements(By.TAG_NAME, 'input')
        # print(d['full_name'].split(" ")[:2])
        first, last = d['full_name'].split(" ")[:2]
        city, nbg = d['city'].replace(" ", "").split(",")[:2]
        review = d['review']

        send_input(inps[0], first)
        send_input(inps[1], last)
        send_input(inps[2], city)
        send_input(inps[3], nbg)

        driver.find_element(By.CSS_SELECTOR, "label[for=':ra:']").click()
        send_input(driver.find_element(By.TAG_NAME, 'textarea'), review)
        upload_image_from_data(d, inps[-1])
        # input("xx")
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
        time.sleep(1)
