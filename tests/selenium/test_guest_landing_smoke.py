import os

import pytest
import requests

pytest.importorskip("selenium")

from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


FRONTEND_URL = os.getenv("FRONTEND_E2E_URL", "http://127.0.0.1:5173")


def _frontend_is_reachable():
    try:
        response = requests.get(FRONTEND_URL, timeout=2)
        return response.ok
    except requests.RequestException:
        return False


@pytest.fixture
def browser():
    if not _frontend_is_reachable():
        pytest.skip(
            f"Frontend is not reachable at {FRONTEND_URL}. Start the Vite app before running Selenium smoke tests."
        )

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--window-size=1440,1000")
    chrome_options.add_argument("--disable-gpu")

    try:
        driver = Chrome(options=chrome_options)
    except WebDriverException as error:
        pytest.skip(f"Chrome/WebDriver is not available for Selenium smoke tests: {error}")

    try:
        yield driver
    finally:
        driver.quit()


@pytest.mark.e2e
@pytest.mark.selenium
def test_guest_landing_smoke(browser):
    browser.get(FRONTEND_URL)
    wait = WebDriverWait(browser, 10)

    try:
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        connect_button = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//button[contains(., 'Connect Spotify') or contains(., 'Login with Spotify')]")
            )
        )
    except TimeoutException as error:
        pytest.fail(f"Guest landing UI did not load successfully: {error}")

    page_heading = browser.find_element(By.TAG_NAME, "h1").text

    assert "Spotify Playlist Generator" in browser.title
    assert connect_button.is_displayed()
    assert "mood" in page_heading.lower()
