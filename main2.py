import random
import os
import time
from urllib.parse import urlparse
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from yaspin import yaspin
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
import requests

load_dotenv()
USERNAME = os.getenv("username")
PASSWORD = os.getenv("password")

# Chrome Options
options = Options()
# options.add_argument("--headless")  # Uncomment for headless mode
options.add_argument("--disable-infobars")
options.add_argument("--disable-extensions")
options.add_argument("--disable-popup-blocking")
options.add_experimental_option("useAutomationExtension", False)
options.add_experimental_option("excludeSwitches", ['enable-automation'])

ua = UserAgent()
user_agent = ua.random
options.add_argument(f"user-agent={user_agent}")

# WebDriver
driver = webdriver.Chrome(service=ChromeService(), options=options)
wait = WebDriverWait(driver, 15)

# Login
with yaspin(text="Logging In ", color="blue", side='right') as spinner:
    login_url = "https://nextdoor.com/login/"
    driver.get(login_url)

    username_field = wait.until(
        EC.presence_of_element_located((By.NAME, "email")))
    password_field = wait.until(
        EC.presence_of_element_located((By.NAME, "password")))

    username_field.send_keys(USERNAME)
    password_field.send_keys(PASSWORD)
    password_field.send_keys(Keys.RETURN)

    wait.until(lambda d: d.current_url != login_url)


def download_image(url, folder='./tmp'):
    if not os.path.exists(folder):
        os.makedirs(folder)
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
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
    name_element = soup.find(
        'span', class_='Styled_color-sm__zpop7k3', string=True)
    full_name = name_element.get_text(strip=True) if name_element else ""
    city_element = soup.find('a', class_='post-byline-redesign')
    city = city_element.get_text(strip=True) if city_element else ""
    review_element = soup.find('span', class_='Linkify')
    review = review_element.get_text(strip=True) if review_element else ""
    image_element = soup.find('div', {'data-testid': 'avatar'}).find('img')
    image_url = image_element['src'] if image_element and image_element.has_attr(
        'src') else None
    return {'full_name': full_name, 'city': city, 'review': review.replace("\n", ""), 'image_url': image_url}


def upload_image_from_data(data_item, upload_input, fallback_folder='images'):
    if data_item.get('image_url'):
        try:
            temp_dir = './tmp'
            image_path = download_image(data_item['image_url'], temp_dir)
            if image_path:
                upload_input.send_keys(os.path.abspath(image_path))
                try:
                    os.remove(image_path)
                except Exception as e:
                    print(f"Error deleting temporary file: {e}")
                return os.path.basename(image_path)
        except Exception as e:
            print(f"Error processing data image: {
                  e}. Falling back to random image.")
    return upload_random_image(fallback_folder, upload_input)


def upload_random_image(image_folder, upload_input):
    image_files = [f for f in os.listdir(
        image_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if not image_files:
        raise ValueError("No images found in the specified folder")
    selected_image = random.choice(image_files)
    image_path = os.path.join(image_folder, selected_image)
    upload_input.send_keys(os.path.abspath(image_path))
    return selected_image


# Scrape recommendations
with yaspin(text="Extracting Reviews ", color="blue", side='right') as spinner:
    post_page = 'https://nextdoor.com/pages/luke-tree-service-seattle-wa/?init_source=search'
    driver.get(post_page)
    wait.until(EC.presence_of_element_located(
        (By.ID, "recommendations-section")))

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
    elements = soup.find_all(attrs={"data-testid": "feed-item-card"})
    data = [extract_feed_item_info(el) for el in elements]


def get_data_subset(data):
    for i, item in enumerate(data):
        print(f" [{i}] - {item['full_name']}")
    print(f"\nTotal items: {len(data)}")
    print("Enter either:")
    print("- A range (e.g., '2-5')")
    print("- Specific indices (e.g., '1,3,5')")
    print("- 'all' for everything")

    while True:
        user_input = input("\nYour selection: ").strip()
        if user_input.lower() == 'all':
            return data
        if '-' in user_input:
            try:
                start, end = map(int, user_input.split('-'))
                return data[start:end + 1]
            except ValueError:
                print("Invalid range format. Use 'start-end'")
        elif ',' in user_input:
            try:
                indices = [int(i) for i in user_input.split(',')]
                return [data[i] for i in indices]
            except ValueError:
                print("Invalid list format. Use comma-separated numbers")
        else:
            try:
                index = int(user_input)
                return [data[index]]
            except ValueError:
                print("Invalid input. Try again.")


def send_input(elmn, text):
    elmn.send_keys(text)


# Select Data
while True:
    data_temp = get_data_subset(data)
    print("Selected data:")
    for d in data_temp:
        print(d['full_name'])
    if input("Confirm [y/n]: ").lower() == "y":
        data = data_temp
        break

# Upload Review
for d in data:
    with yaspin(text=f"Uploading Review: {d['full_name']} ", color="blue", side='right') as spinner:
        review_url = "https://luketreeservice.com/review"
        driver.get(review_url)

        inps = wait.until(
            EC.presence_of_all_elements_located((By.TAG_NAME, 'input')))
        print(d)
        first, last = d['full_name'].split(" ")[:2]
        city, nbg = d['city'].replace(" ", "").split(",")[:2]
        review = d['review']

        send_input(inps[0], first)
        send_input(inps[1], last)
        send_input(inps[2], city)
        send_input(inps[3], nbg)

        wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "label[for=':ra:']"))).click()
        send_input(driver.find_element(By.TAG_NAME, 'textarea'), review)
        upload_image_from_data(d, inps[-1])
        # wait.until(EC.element_to_be_clickable(
        #     (By.CSS_SELECTOR, "button[type='submit']"))).click()
        # time.sleep(1)
        input("Next")
