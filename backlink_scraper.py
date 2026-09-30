import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time

def main():
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    driver = uc.Chrome(options=options)
    try:
        query = "buy bulk gmail account"
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        driver.get(url)
        time.sleep(2)  # wait for the page to load
        results = driver.find_elements(By.CSS_SELECTOR, "div.yuRUbf a")
        links = [result.get_attribute("href") for result in results]
        print("Backlink opportunities:")
        for link in links:
            print(link)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()