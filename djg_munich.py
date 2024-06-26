import json
import os
import time
from typing import Union, List, Dict, Tuple

import pathvalidate as pathvalidate
import requests
import selenium.common
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement


def start_webdriver() -> webdriver:
    """
    Starts a Firefox WebDriver instance with custom preferences.

    :param None:
    :type None:
    :return A started Firefox WebDriver instance.
    :rtype webdriver.Firefox
    """
    firefox_options = Options()
    firefox_options.set_preference("media.autoplay.default", False)
    firefox_options.set_preference("javascript.enabled", True)

    # firefox_options.headless = False
    # firefox_options.add_argument('-headless')

    driver = webdriver.Firefox(options=firefox_options)

    return driver


def execute_with_exception_handling(driver: webdriver, by_filter: By, filter_name: str, all_elements: bool = False) \
        -> Union[List[WebElement], WebElement]:
    """
    execute_with_exception_handling is a function that executes a search for an element on the web page using
    Selenium WebDriver. It handles exceptions and returns the found elements or None if not found.

    :param driver: The Selenium WebDriver object used to interact with the webpage.
    :type driver: webdriver
    :param by_filter: The type of filter to use when searching for the element (e.g., By.ID, By.CLASS_NAME, etc.).
    :type by_filter: By
    :param filter_name: The name of the element to search for.
    :type filter_name: str
    :param all_elements: A boolean flag indicating whether to find all elements with the given filter or just one.
    :type all_elements: bool, optional

    :return: The found elements if successful, None otherwise.
    :rtype: list | WebElement
    """
    try:
        if all_elements:
            data = driver.find_elements(by_filter, filter_name)
        else:
            data = driver.find_element(by_filter, filter_name)
    except selenium.common.NoSuchElementException:
        data = None
        print("Couldn't find element {} with filter {}!".format(filter_name, by_filter))
    return data


def click_alpha_navigation_button(i: int, driver: webdriver, element: WebElement) \
        -> Tuple[WebElement, List[WebElement]]:
    """
    Clicks an alpha navigation button based on the given index `i` and Selenium driver.

    :param i: The index of the navigation button to click, defaults to None
    :type i: int
    :param driver: The Selenium WebDriver instance
    :type driver: selenium.webdriver
    :param element: The UI element from which to start clicking buttons
    :type element: selenium.webdriver.By

    :return: A tuple containing the accordion item and button elements
    :rtype: tuple(selenium.webdriver.WebElement, list[selenium.webdriver.WebElement])
    """

    if i != 0:
        element.click()

    time.sleep(2)

    # navigation buttons
    accordion_item = execute_with_exception_handling(driver, By.TAG_NAME, "ul", all_elements=True)[1]
    button_elements = execute_with_exception_handling(accordion_item, By.XPATH, './/button', all_elements=True)

    return accordion_item, button_elements


def process_webpage_elements(j: int, element: WebElement, accordion_item: WebElement, buttons: List[str]) -> Dict:
    """
    process_webpage_elements is a function that processes elements from a webpage. It takes in four parameters:
    j, element, accordion_item, and buttons. This function simulates clicks on the webpage, retrieves text and images
    from specific locations, and returns the processed data as a dictionary.

    :param j: The index of the button to click.
    :type j: int

    :param element: A browser element that is used to simulate clicks.
    :type element: Selenium WebElement

    :param accordion_item: A browser element representing an accordion item.
    :type accordion_item: Selenium WebElement

    :param buttons: A list of text strings representing the buttons on the webpage.
    :type buttons: list[str]

    :return: A dictionary containing the processed data from the webpage, including the button text, text box contents,
    and image URLs.
    :rtype: dict
    """
    if j != 0:
        element.click()

    time.sleep(3)

    data_container = {}

    button_text = buttons[j]
    data_container["header"] = button_text

    text_box = execute_with_exception_handling(accordion_item, By.XPATH, '//div[@data-hook="children"]')
    if text_box:
        text_box = text_box.text
        data_container["text"] = text_box

    image_boxes = execute_with_exception_handling(accordion_item, By.XPATH, '//img', all_elements=True)

    images = []
    for i, image_box in enumerate(image_boxes):
        image_url = image_box.get_attribute("src")
        images.append(image_url)

        # download images and save them to image dir
        response = requests.get(image_url)
        if response.status_code == 200:

            sanitized_filename = pathvalidate.sanitize_filename(f"{button_text}_{i}")
            filename = f"./images/{sanitized_filename}.png"

            with open(filename, 'wb+') as f:
                f.write(response.content)

    data_container["images"] = images

    return data_container


def load_website(driver: webdriver, url: str) -> Dict:
    """
    Loads a website and extracts relevant information.

    :param driver: Selenium WebDriver object
    :param url: URL of the website to load

    :type driver: selenium.webdriver.WebDriver
    :type url: str

    :return: A dictionary containing extracted data from the website, organized by alpha navigation buttons
    :rtype: dict
    """

    driver.implicitly_wait(10)

    # get website and wait
    driver.get(url)

    driver.execute_script('window.scrollTo(0, 100);')

    time.sleep(5)

    extracted_data = {}

    main_text = execute_with_exception_handling(driver, By.TAG_NAME, "main")
    if main_text:
        main_text = main_text.text
        extracted_data["main"] = main_text

    wait = WebDriverWait(driver, 10)
    content_iframe = execute_with_exception_handling(driver, By.TAG_NAME, "iframe")
    # wait for appearance of the iframe
    content_iframe = wait.until(EC.visibility_of(content_iframe))

    # switch to iframe to access async loaded webpage with the content we want
    driver.switch_to.frame(content_iframe)

    # 0 = f&a navigation, 1 = content
    ul_elements_in_iframe = execute_with_exception_handling(driver, By.TAG_NAME, "ul", all_elements=True)

    # alphabet navigation buttons
    alpha_nav_buttons = execute_with_exception_handling(ul_elements_in_iframe[0], By.XPATH, './/div', all_elements=True)

    for i, a_nav in enumerate(alpha_nav_buttons):
        alpha = a_nav.text
        extracted_data[alpha] = {}

        # check if navigation is clickable
        element = wait.until(EC.element_to_be_clickable(a_nav))

        accordion_item, button_elements = click_alpha_navigation_button(i, driver, element)
        buttons = list(map(lambda x: x.text, button_elements))

        for j, button in enumerate(button_elements):
            element = wait.until(EC.element_to_be_clickable(button))

            data_container = process_webpage_elements(j, element, accordion_item, buttons)

            extracted_data[alpha][f"page_{j}"] = data_container

    return extracted_data


def make_img_dir():
    if not os.path.exists('./images'):
        os.mkdir('./images')


def start_extraction(url: str):
    """
    Starts the extraction process by loading a website using Selenium and Firefox WebDriver. The result is saved to a
    json file.

    :param url: The URL of the website to extract content from.
    :type url: str
    :returns: None
    :rtype: None
    """

    make_img_dir()

    firefox_webdriver = start_webdriver()
    extracted_content = load_website(firefox_webdriver, url)
    firefox_webdriver.quit()

    json.dump(extracted_content, open('./djg_munich.json', 'w+', encoding='utf-8'), indent=True, ensure_ascii=False)


if __name__ == '__main__':
    start_extraction('https://www.djg-muenchen.de/japan-a-z')
