from playwright.async_api import async_playwright
import asyncio
import time
import json
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

async def amazon_navigation_crawl4ai(url, email, password):
    # Step 1: Define the login and navigation JavaScript
    login_js = f"""
        document.querySelector('#nav-link-accountList').click();
        setTimeout(() => {{
            document.querySelector('input[name="email"]').value = '{email}';
            document.querySelector('input[type="submit"][aria-labelledby="continue-announce"]').click();
        }}, 2000);
        setTimeout(() => {{
            document.querySelector('input[name="password"]').value = '{password}';
            document.querySelector('input#signInSubmit').click();
        }}, 4000);
    """

    # Step 2: Search for 'samsung' after login
    search_js = """
        setTimeout(() => {
            document.querySelector('input#twotabsearchtextbox').value = 'samsung';
            document.querySelector('input#nav-search-submit-button').click();
        }, 2000);
    """

    # Step 3: Extract product links using CSS selectors
    product_links_schema = {
        "name": "AmazonProductLinks",
        "baseSelector": "a.a-link-normal.s-line-clamp-2.s-line-clamp-3-for-col-12.s-link-style.a-text-normal",
        "fields": [
            {"name": "href", "selector": "", "type": "attribute", "attribute": "href"}
        ]
    }

    # Step 4: Extract review links on product page
    review_links_schema = {
        "name": "AmazonReviewLinks",
        "baseSelector": "a.a-link-emphasis.a-text-bold",
        "fields": [
            {"name": "href", "selector": "", "type": "attribute", "attribute": "href"}
        ]
    }

    browser_conf = BrowserConfig(headless=False, verbose=True)
    async with AsyncWebCrawler(config=browser_conf) as crawler:
        # Login and search
        config_login = CrawlerRunConfig(
            js_code=[login_js, search_js],
            wait_for="css:input#twotabsearchtextbox",
            delay_before_return_html=6
        )
        result_login = await crawler.arun(url=url, config=config_login)
        
        # Extract product links
        config_products = CrawlerRunConfig(
            extraction_strategy=JsonCssExtractionStrategy(product_links_schema),
            wait_for="css:a.a-link-normal.s-line-clamp-2",
            delay_before_return_html=5
        )
        result_products = await crawler.arun(url=url, config=config_products)
        product_links = []
        if result_products.success and result_products.extracted_content:
            import json
            product_links = [url + item['href'] for item in json.loads(result_products.extracted_content)]
        if not product_links:
            print("No product links found.")
            return

        # Visit first product page and extract reviews
        config_reviews = CrawlerRunConfig(
            extraction_strategy=JsonCssExtractionStrategy(review_links_schema),
            wait_for="css:a.a-link-emphasis.a-text-bold",
            delay_before_return_html=5
        )
        result_reviews = await crawler.arun(url=product_links[0], config=config_reviews)
        review_links = []
        if result_reviews.success and result_reviews.extracted_content:
            review_links = [url + item['href'] for item in json.loads(result_reviews.extracted_content)]
        for link in review_links:
            print("Review link:", link)
        # Optionally, save HTML or visit review pages as needed

def write_markdown_content(content, file_path):
    """
    Write content to a markdown file.
    
    Args:
        content (str): Content to write
        file_path (str): Path to the output file
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

async def amazon_navigation_async(url, email, password):
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(url)
        # signin_check = page.locator(selector= '', has_text='signin')
        # print(f'print signin locator : {signin_check}')
        # write_html_to_file(landing_page, 'landing_page.html')
        time.sleep(4)
        await asyncio.sleep(2)
        await page.click('#nav-link-accountList')
        await asyncio.sleep(5)
        await page.fill('input[name="email"]', email)
        await page.click('input[type="submit"][aria-labelledby="continue-announce"]')
        await asyncio.sleep(2)

        await page.fill('input[name="password"]', password)
        await page.click('input#signInSubmit')
        await asyncio.sleep(2)

        await page.wait_for_selector('#nav-link-accountList-nav-line-1', timeout=10000)
        print("Logged in as:", await page.inner_text('#nav-link-accountList-nav-line-1'))

        await page.fill('input#twotabsearchtextbox', 'iphone')
        await page.click('input#nav-search-submit-button')
        await asyncio.sleep(4)
        anchors = await page.query_selector_all('a.a-link-normal.s-line-clamp-2.s-line-clamp-3-for-col-12.s-link-style.a-text-normal')
        
        hrefs = [await a.get_attribute('href') for a in anchors]
        all_prodLinks = []
        product_count = 1
        for link in hrefs:
            product_complete_link = f"{url}{link}"
            all_prodLinks.append(product_complete_link)
            product_page = await context.new_page()
            await product_page.goto(product_complete_link)
            await product_page.wait_for_load_state('domcontentloaded')
            time.sleep(3)
            all_review_anchor = await product_page.query_selector_all('a.a-link-emphasis.a-text-bold')
            review_final_links = [await a.get_attribute('href') for a in all_review_anchor]

            complete_review_link = f"{url}{review_final_links[0]}"
            time.sleep(4)
            review_page = await context.new_page()
            await review_page.goto(complete_review_link)
            await product_page.wait_for_load_state('domcontentloaded')
            time.sleep(3)
            
            loop_true = True
            review_count = 1
            md_generator = DefaultMarkdownGenerator()
            while loop_true:
                time.sleep(4)
                review_html = await review_page.content()
                md_result = md_generator.generate_markdown(input_html=review_html)
                markdown_content = md_result.markdown_with_citations
                path = f'product:{product_count}_review:{review_count}_review_page.md'
                write_markdown_content(markdown_content, path)
            
                next_button =  review_page.locator(selector='li.a-last',has_text='next page')
                next_button_disabled = review_page.locator(selector='li.a-disabled.a-last',has_text='next page')
                
                bb_count = await next_button.count()
                disabled_next_btn_count = await next_button_disabled.count()

                if(bb_count > 0 and disabled_next_btn_count == 0): 
                    await review_page.click('li.a-last')
                else:
                    loop_true=False
            
                
                review_count += 1
            print(f'scanned all reviews for link : {link} ')
            await review_page.close()
            product_count += 1
            time.sleep(3)
            await product_page.close()

        # product_page = await context.new_page()
        # await product_page.goto(all_prodLinks[0])
        # await asyncio.sleep(4)
        # # Save product page HTML
        # product_html = await product_page.content()
        # write_html_to_file(product_html, 'product_page.html')
        
        # # await product_page.wait_for_selector('a[data-hook="see-all-reviews-link-foot"]')
        # # await product_page.wait_for_load_state('domcontentloaded')
        # # await product_page.click('a[data-hook="see-all-reviews-link-foot"]')
        # # await product_page.click('a.a-link-emphasis.a-text-bold')
        # # # await page.wait_for_selector('a.a-link-emphasis.a-text-bold', state='attached', timeout=10000)
        # all_review_anchor = await product_page.query_selector_all('a.a-link-emphasis.a-text-bold')

        # print("Logged in as:", await page.inner_text('#nav-link-accountList-nav-line-1'))
        # review_final_links = [await a.get_attribute('href') for a in all_review_anchor]
        # ff_review_links = []
        # await asyncio.sleep(5)
        # for link in review_final_links:
        #     complete_link = f"{url}{link}"
        #     ff_review_links.append(complete_link)
        #     print(complete_link)
        #     print("*************")


        # for link in ff_review_links:
        #     review_page = await context.new_page()
        #     await review_page.goto(link)
        #     await asyncio.sleep(2)

        #     loop_true = True
        #     while loop_true:
        #         time.sleep(4)
        #         next_button =  review_page.locator(selector='li.a-last',has_text='next page')
        #         next_button_disabled = review_page.locator(selector='li.a-disabled.a-last',has_text='next page')
                
        #         bb_count = await next_button.count()
        #         disabled_next_btn_count = await next_button_disabled.count()

        #         if(bb_count > 0 and disabled_next_btn_count == 0): 
        #             print(next_button)
        #             await review_page.click('li.a-last')
        #         else:
        #             loop_true=False
            
        #         print(f'scanned all reviews for link : {link} ')
        #     review_page.close()

            # counter = 3
            # while counter > 0:
            #     next_button1 = review_page.locator(selector='li.a-last',has_text='next page')
            #     btn_counts = await next_button1.count()
            #     print(f'{next_button1} , btn_counts : {btn_counts}')



            #     next_button2 = review_page.locator(selector='a',has_text='next page')
            #     btn_counts2 = await next_button2.count()
            #     print(f'{next_button2} , btn_counts : {btn_counts2}')


            #     await review_page.click('li.a-last')
            #     counter -= 1
            #     time.sleep(10)


            # buttons_pagination_section = await review_page.query_selector('ul.a-pagination')
            # button  = await buttons_pagination_section.query_selector_all('li')
            
            # if list size is 1 then this is the last page.
            
            # nav = await review_page.query_selector('ul.a-pagination')
            # nav_button = await nav.query_selector_all('li')
            # print(f'first nav next button : {nav_button}')
            # await nav_button[0].click()
            # time.sleep(5)
            # print('clicking on the next link ')
            # nav = await review_page.query_selector('ul.a-pagination')
            # nav_button = await nav.query_selector_all('li')
            # print(f'second nav next button : {nav_button}')
            # await nav_button[1].click()

            # while(len(nav_button) >= 2):

                

            #     next_page = await button[0].click()

            # print(f'previous_page : {previous_page} , next_page : {next_page_anchor.text_content} ')

            # time.sleep(1000)
            # Save review page HTML
            # review_html = await review_page.content()

            # md_generator = DefaultMarkdownGenerator()

            # Generate markdown from the HTML
            # md_result = md_generator.generate_markdown(input_html=review_html)

            # Access the markdown outputs
            # print("Raw Markdown:\n", md_result.raw_markdown)
            # print("Markdown with Citations:\n", md_result.markdown_with_citations)
            # print("References Markdown:\n", md_result.references_markdown)
            # print("Fit Markdown (if filter used):\n", md_result.fit_markdown)

            # write_html_to_file(review_html, 'review_page.html')
        await browser.close()
    return



# def generate_markdown(html_list):
#     md_generator = DefaultMarkdownGenerator()
#     for html in html_list:
#         md_result = md_generator.generate_markdown(input_html=html)
#         write_html_to_file(md_result,)


def amazon_login(email, password):
    final_cookies = ""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Headless=False to see the browser
        context = browser.new_context()
        page = browser.new_page()

        # Go to Amazon homepage
        page.goto("https://www.amazon.in/")

        time.sleep(10)
        # Click the "Hello, Sign in" link
        page.click('#nav-link-accountList')
        

        # Wait and fill login
        time.sleep(10)
        page.fill('input[name="email"]', email)
        # Click the "Continue" button by input element
        page.click('input[type="submit"][aria-labelledby="continue-announce"]')
        time.sleep(5)

        # Fill password
        page.fill('input[name="password"]', password)
        page.click('input#signInSubmit')
        time.sleep(6)

        # Optional: Wait for successful login indicator
        page.wait_for_selector('#nav-link-accountList-nav-line-1', timeout=10000)
        print("Logged in as:", page.inner_text('#nav-link-accountList-nav-line-1'))

        # Get document.cookie from the page
        cookies = page.evaluate("() => document.cookie")
        final_cookies = cookies
        print("document.cookie:", cookies)

        time.sleep(5)
        browser.close()
    return final_cookies


def parse_kv_string(s):
    return [item.split('=') for item in s.split(';')]

def dump_to_env_file(array, filename=".env_current_login"):
    with open(filename, "w") as f:
        for key, value in array:
            f.write(f"{key}={value}\n")

def write_env_json_file(array,file_name):
     # Ensure array is a list of pairs
    if len(array) == 1 and isinstance(array[0], list) and len(array[0]) == 2:
        data_dict = {array[0][0]: array[0][1]}
    else:
        data_dict = dict(array)
    # Write to file
    with open(file_name, "w") as f:
        json.dump(data_dict, f)
    return

def read_env_json_file(file_name):
    try:
        with open(file_name, "r") as f:
            loaded_dict = json.load(f)
        return loaded_dict
    except FileNotFoundError:
        print(f"File not found: {file_name}")
        return {}
    except json.JSONDecodeError:
        print(f"Error decoding JSON in file: {file_name}")
        return None

def surf_amazon(cookies):
    # cookie_values = read_env_json_file(cookies_file_path)
    # cookie_values = {
    #     "session-id":"260-4147975-2194308",
    #     "ubid-acbin":"262-8624452-5314833",
    #     "csm-sid":"958-4817579-4573129",
    #     "i18n-prefs":"INR",
    #     "lc-acbin":"en_IN",
    #     "session-token":"kWHSb2e0+JC0Xp1GRZQLehoak/plTg9p61bJXTzbyDDgczm+e0g52G4a7oAb+GbyH5EhoLr8/gkksJGmR9BHoc6ldFAe1Ot+8kfxI4B9QXs683wdr/aY3W1K90URVrHpHC+ZkIY64YgyrWyQCKSxHa0C3CiIAdub4Kh6CRfG+DzX8NGHmWmH7frpG64WLnAvhU7eRKJ+aY85N0rNTZRj+X/8Yt1mBgyoC2dCIK4Ttw2nZD8/n6uQrTb2UliqeOtNsgNFeqSWOug6P29vMSE6Gu0/JU7+dEfISgGnza7GBn0sWS3TimgbhNtB/lEaUbiMzXXTHcWiLWozxu10jrpPatvfAyCDnl1ogwGkr+RXRcrOgszRuBVOAEoZeV0EN0rF",
    #     "x-acbin":"V5c8L?8jy?PvIj1Fsvlcj2X4sUBvwTq31xqy2SHVOJlHDY6UJEqJ0XT6CNbPhos7",
    #     "session-id-time":"2082787201l",
    #     "csm-hit":"tb:M9PGPFTA9AW79CB6BSTR+s-M9PGPFTA9AW79CB6BSTR|1751975858228&t:1751975858228&adb:adblk_no",
    #     "rxc":"AItxZ1DbuZg+2qM2Blg"
    # }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()

        # Prepare cookies list
        cookies = [{
            "name": name,
            "value": value,
            "domain": ".amazon.in",     # Replace with correct domain if different
            "path": "/",
            "httpOnly": True,
            "secure": True,
            "sameSite": "Lax"
        } for name, value in cookies.items()]

        # Set cookies
        context.add_cookies(cookies)
        time.sleep(5)        

        page = context.new_page()
        page.goto("https://www.amazon.in/")
        time.sleep(15)


        print("All specified cookies have been set.")

        # Keep the browser open briefly
        page.wait_for_timeout(10000)  # 10 seconds
        browser.close()

import asyncio
from playwright.sync_api import sync_playwright

def check_login_status(cookies):
    login_status  = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()

            cookies = [{
                "name": name,
                "value": value,
                "domain": ".amazon.in",     # Replace with correct domain if different
                "path": "/",
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax"
            } for name,value in cookies.items()]

            context.add_cookies(cookies)
            page = context.new_page()
            time.sleep(2)

            page.goto("https://www.amazon.in")
            time.sleep(5)
            # Wait for the span element to load
            page.wait_for_selector("#nav-link-accountList-nav-line-1")
            # Get the text content of the element
            greeting_text = page.inner_text("#nav-link-accountList-nav-line-1")

            if "sign in" in greeting_text.lower():
                print("❌ Not logged in")
                login_status = False
            else:
                print(f"✅ Logged in as: {greeting_text}")
                login_status = True
            browser.close()
    except Exception as e:
        print(f"Exception occurred in check_login_status: {e}")
        login_status = None
        try:
            browser.close()
        except:
            pass
    return login_status


def form_cookies_array(str):
    import re
    output = []
    subStr = str.split(';')
    for item in subStr:
        key = item.split('=')[0].strip()
        value_pattern = r"\".*\""
        value_regex = re.search(value_pattern,item)
        
        if value_regex==None:
            value = item.split('=')[1].strip()
            output.append([key,value])
        else:
            value = value_regex.group().strip('"').strip()
            output.append([key,value])
    return output

def write_dict_to_env(array, file_name):
    # Ensure array is a list of pairs
    try:
        if len(array) == 1 and isinstance(array[0], list) and len(array[0]) == 2:
            data_dict = {array[0][0]: array[0][1]}
        else:
            data_dict = dict(array)

        with open(file_name, "w") as f:
            for key, value in data_dict.items():
                f.write(f"{key}={value}\n")
        return True
    except Exception as e:
        print(f"Exception occurred in write_dict_to_env: {e}")
        return False

def get_fresh_cookies(creds_file_path):
    import os
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=creds_file_path)
    email = os.getenv('AMAZON_EMAIL')
    password = os.getenv('AMAZON_PASSWORD')
    cookies = amazon_login(email=email,password=password)
    return cookies

def store_fresh_cookies(browser_cookies_filepath,cookies):
    cookies_array = form_cookies_array(cookies)
    return write_dict_to_env(cookies_array,browser_cookies_filepath)

    
def get_amazon_cookies(browser_cookies_filepath,creds_file_path):
    print(f'reading existing cookies from file : {browser_cookies_filepath}')
    cookies = read_env_file(browser_cookies_filepath)

    print(f'checking authentication criteria')
    login_status = check_login_status(cookies=cookies)
    if login_status==True:
        print(f'Existing cookies worked.. returing cookies....')
        return cookies
    elif login_status==False:
        print(f'Authentication failed with existing cookies, getting fresh cookies!!!, Readin creds file :{creds_file_path}')
        new_cookies = get_fresh_cookies(creds_file_path)

        print(f'Storing fresh cookies!!!!!! , to file : {browser_cookies_filepath}')
        status = store_fresh_cookies(browser_cookies_filepath,new_cookies)
        if(status==True):
            print('stored fresh cookies successfully...')
        else:
            print('Failed to store fresh cookies..')
        return read_env_file(browser_cookies_filepath)


def read_env_file(filename):
    try:
        env_dict = {}
        with open(filename, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue  # Skip empty lines and comments
                if "=" in line:
                    key, value = line.split("=", 1)
                    env_dict[key] = value
        return env_dict
    except FileNotFoundError:
        print(f"File not found: {filename}")
        return None

def amazon_cookies_handler():
    browser_cookies_filePath = '.env_temp_browser_cookies'
    creds_filepath = '.env'
    cookies = get_amazon_cookies(browser_cookies_filepath=browser_cookies_filePath,creds_file_path=creds_filepath)
    return cookies

def write_html_to_file(html_content, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)

def extract_markdown_from_html_file(html_file_path, output_md_path=None):
    """
    Reads HTML from a file, uses crawl4ai to extract markdown, and optionally writes it to a file.
    """
    async def _extract():
        browser_conf = BrowserConfig(headless=True)
        run_conf = CrawlerRunConfig()
        
        # Read HTML content from file
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        async with AsyncWebCrawler(config=browser_conf) as crawler:
            # Use the crawler's extract_markdown_from_html method if available
            if hasattr(crawler, 'extract_markdown_from_html'):
                result = await crawler.extract_markdown_from_html(html_content)
                markdown = result.markdown if hasattr(result, 'markdown') else result
            else:
                # Fallback: Use a temporary file or custom method if needed
                raise NotImplementedError("Your version of crawl4ai may not support direct HTML-to-markdown extraction.")
        
        if output_md_path:
            with open(output_md_path, 'w', encoding='utf-8') as f:
                f.write(markdown)
        return markdown

    return asyncio.run(_extract())


if __name__ == "__main__":

    #algorithm
    browser_cookies_filePath = '.env_temp_browser_cookies'
    creds_filepath = '.env'
    url = 'https://amazon.in'
    # cookies = get_amazon_cookies(browser_cookies_filepath=browser_cookies_filePath,creds_file_path=creds_filepath)
    # print(cookies)
    import os
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=creds_filepath)
    email = os.getenv('AMAZON_EMAIL')
    password = os.getenv('AMAZON_PASSWORD')

    asyncio.run(amazon_navigation_async(url=url,email=email,password=password))
    # asyncio.run(amazon_navigation_crawl4ai("https://www.amazon.in/", "your_email", "your_password"))
    # cookies = amazon_cookies_handler()
    # print(cookies)
    '''
    1. Read teh .env_temp_browser_cookies
    2. If found no cookies, 
        COLLECT_AND_SAVE_COOKIES : 
            then get email and password and login into the amazon ,  collect cookies and save it in .env_temp_browser_cookies file for further use.
    3. If found cookies, check the authencity of cookies, if it got expired, then follow `COLLECT_AND_SAVE_COOKIES` step
    4. If found cookies which are working, then start surfing amazon website.
    5. Search a product , list down the product details and its reviews.
    '''
