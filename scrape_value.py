# -*- coding: utf-8 -*-
"""Yahoo! Fantasy Football Auction Draft Value Scraper

This module scrapes the top 350 players from the Yahoo! Fantasy Football Auction Draft Analysis and writes them out
to a CSV file that can later be used for spreadsheets to aid in drafting.
"""

from selenium import webdriver
from typing import Dict, List

import argparse
import csv
import logging.config

# Import logging config
logging.config.fileConfig('logging.conf')
# Get logger
logger = logging.getLogger('root')

YAHOO_RESULTS_PER_PAGE = 50  # Static but used to calculate offsets for loading new pages

fields = ['Name', 'Position', 'Team', 'Projected Value', 'Average Cost', 'Percent Drafted']

XPATH_MAP = {
    'Name': 'td[1]/div/div[1]/div/a',
    'Position': 'td[1]/div/div[1]/div/span',
    'Projected Value': 'td[2]/div',
    'Average Cost': 'td[3]/div',
    'Percent Drafted': 'td[4]/div'
}

# Type aliases
SeleniumDriver = webdriver.chrome.webdriver.WebDriver
SeleniumWebElement = webdriver.remote.webelement.WebElement


def process_player(player_row: SeleniumWebElement) -> Dict[str, str]:
    """
    Process the row containing a player's auction values and return the values in a dict.

    :param player_row: Selenium webelement containing a player's info and auction values
    :return: Dictionary containing the auction values retrieved from the row provided
    """
    draft_values = {}

    logger.debug('%s', player_row.text.replace('\n', ' '))

    # Grab all the values for this player
    for col_name, xpath in XPATH_MAP.items():
        # Retrieve each value based on the xpath map
        draft_values[col_name] = player_row.find_element_by_xpath(xpath).get_attribute('innerHTML')

    # Position and Team reside in the same element, parse them add and place them separately
    team, position = draft_values['Position'].split(' - ')
    draft_values['Position'] = position
    draft_values['Team'] = team

    return draft_values


def process_page(driver: SeleniumDriver, cnt: int) -> List[Dict[str, str]]:
    """
    Process a page containing multiple rows of players and their auction draft values, returning a list. Each element
    of the list represents one player and their auction draft values.

    :param driver: Selenium web driver used to grab the HTML
    :param cnt: Current count to determine which page to scrape
    :return: List where each element is a dict containing a player's auction draft values
    """

    logger.info('Getting stats for count %d', cnt)

    # Load the page containing the table with draft auction values
    url = 'https://football.fantasysports.yahoo.com/f1/draftanalysis?tab=AD&pos=ALL&sort=DA_PC&count=%d' % (cnt,)
    driver.get(url)

    # Base xpath for all the rows
    base_xpath = '//*[@id="draftanalysistable"]/tbody/tr'

    # Grab the rows then parse each one, creating a list of dictionaries where each dictionary represents one player
    rows = driver.find_elements_by_xpath(base_xpath)

    auction_values_list = []
    for row in rows:
        stats_item = process_player(row)
        auction_values_list.append(stats_item)

    if len(auction_values_list) < YAHOO_RESULTS_PER_PAGE:
        logging.warning('Only scraped %d rows @ count %d, expected to scrape %d',
                        len(auction_values_list), cnt, YAHOO_RESULTS_PER_PAGE)

    return auction_values_list


def write_auction_draft_values(auction_values_list: List[Dict[str, str]], out_filename: str) -> None:
    """
    Write out the list of auction draft values to a csv file.

    :param auction_values_list: List where each element is a dict containing a player's auction draft values
    :param out_filename: Filename of the output csv where the auction draft values will be written
    """
    logger.info('Writing to file %s', out_filename)

    # Specify newline and encoding to have consistent output across platforms
    with open(out_filename, 'w', newline="\n", encoding="utf-8") as f:
        csv_writer = csv.DictWriter(f, delimiter=',', fieldnames=fields)

        csv_writer.writeheader()
        for row in auction_values_list:
            csv_writer.writerow(row)


def get_auction_draft_values(csv_file: str, total_players: int) -> None:
    """
    Scrape the auction draft values for the specified number of players and write out the values to the file specified.

    :param csv_file: Filename of the csv where the values will be written
    :param total_players: Number of players to scrape
    """

    # Startup the selenium webdriver based on Chrome
    driver = webdriver.Chrome()
    # Allow up to 30 seconds for the page to load before throwing an error
    driver.set_page_load_timeout(30)

    auction_values_list = []
    for cnt in range(0, total_players, YAHOO_RESULTS_PER_PAGE):
        page_stats = process_page(driver, cnt)
        auction_values_list.extend(page_stats)

    # Log a warning if we didn't scrape the number of players asked for
    if len(auction_values_list) < total_players:
        logging.warning('Only scraped %d rows @, expected to scrape %d',
                        len(auction_values_list), total_players)

    # Write out the scraped stats to the csv file
    write_auction_draft_values(auction_values_list, csv_file)

    # Close the selenium webdriver
    driver.close()

if __name__ == '__main__':

    # Parse the command line arguments
    parser = argparse.ArgumentParser(description='Yahoo! Fantasy Football Auction Draft Value Scraper')
    parser.add_argument('-f', '--out_filename', type=str, default='stats.csv', help='Filename of the output csv')
    parser.add_argument('-n', '--num_players', type=int, default=350, help='Number of players to scrape')
    parser.add_argument('-d', '--debug', action='store_true', default=False, help='Enable debug prints')

    args = parser.parse_args()

    # If debug mode requested, enable debug logging
    if args.debug:
        logger.setLevel(logging.DEBUG)

    get_auction_draft_values(args.out_filename, args.num_players)
