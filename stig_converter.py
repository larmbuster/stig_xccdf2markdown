import os
import requests
import zipfile
import lxml.etree as ET
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager
from urllib.parse import urljoin
from typing import Optional, Tuple, List, Dict, Any
import time
import random
import argparse
import sys
import platform
import io

# Fix console encoding for Windows
if platform.system() == "Windows":
    # Set console encoding to UTF-8 for Windows
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# --- Configuration ---
# Support environment variables for container deployments while maintaining defaults for local use
BASE_URL = os.environ.get('STIG_BASE_URL', "https://www.cyber.mil/stigs/downloads/")
DOWNLOAD_DIR = os.environ.get('STIG_DOWNLOAD_DIR', "stig_downloads")
OUTPUT_DIR = os.environ.get('STIG_OUTPUT_DIR', "stig_markdown_output")
XSLT_FILE = os.environ.get('STIG_XSLT_FILE', "xccdf_to_markdown.xsl")

# Container detection - helps optimize settings when running in Podman
IS_CONTAINER = os.environ.get('CONTAINER_ENV', 'false').lower() == 'true'


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent directory traversal attacks.
    
    Removes path separators and other dangerous characters from filenames.
    This prevents attacks like "../../etc/passwd" from escaping the intended directory.
    
    Args:
        filename: The filename to sanitize
        
    Returns:
        A sanitized filename safe for use in os.path.join()
    """
    # Remove path separators and other dangerous characters
    filename = os.path.basename(filename)
    # Remove any remaining path components
    filename = filename.replace('/', '').replace('\\', '')
    # Remove null bytes
    filename = filename.replace('\x00', '')
    return filename


def create_directories():
    """
    Create necessary directories if they don't exist.
    
    Creates the download and output directories as specified by the DOWNLOAD_DIR
    and OUTPUT_DIR configuration variables. Uses exist_ok=True to avoid errors
    if directories already exist.
    """
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Created/verified directories: '{DOWNLOAD_DIR}' and '{OUTPUT_DIR}'")

def get_stig_zip_links(headless: bool = True, max_pages_limit: Optional[int] = None) -> Tuple[List[str], List[Dict[str, Any]], int, int, int]:
    """
    Scrape the STIG download page using Selenium to find all download links.
    
    This function navigates through paginated content on the cyber.mil STIG downloads
    page, extracts all links to STIG.zip files, and returns them along with browser
    session cookies for use in subsequent downloads.
    
    Args:
        headless: Run browser in headless mode (default: True)
        max_pages_limit: Maximum number of pages to process. If None, processes up to
                        200 pages or until no new content is found (default: None)
    
    Returns:
        A tuple containing:
        - absolute_links: List of absolute URLs to STIG.zip files
        - cookies: List of browser session cookies (for use with requests library)
        - pages_processed: Number of pages processed during scraping
        - total_download_buttons_analyzed: Total number of download buttons found
        - total_stig_zip_matches: Total number of STIG.zip links found (including duplicates)
        
        On error, returns: ([], [], 0, 0, 0)
    """
    print(f"Scraping {BASE_URL} for STIG .zip file links...")
    if max_pages_limit:
        print(f"Limiting to {max_pages_limit} pages for testing")
    
    # Detect operating system
    system = platform.system()
    is_macos = system == "Darwin"
    is_windows = system == "Windows"
    is_linux = system == "Linux"
    
    # Set up Firefox options to mimic human browsing behavior
    firefox_options = Options()
    
    # Container-specific optimizations
    if IS_CONTAINER:
        print("Container environment detected - applying container optimizations")
        firefox_options.add_argument("--headless")  # Always headless in containers
        firefox_options.add_argument("--no-sandbox")
        firefox_options.add_argument("--disable-dev-shm-usage")
        firefox_options.add_argument("--disable-gpu")
        firefox_options.add_argument("--disable-software-rasterizer")
        firefox_options.add_argument("--disable-extensions")
        
        # Increase shared memory size
        firefox_options.add_argument("--shm-size=2g")
        
        # Set preferences for better stability in containers
        firefox_options.set_preference("dom.ipc.plugins.enabled.libflashplayer.so", False)
        
        # Disable caching in containers for better memory usage
        firefox_options.set_preference("browser.cache.disk.enable", False)
        firefox_options.set_preference("browser.cache.memory.enable", False)
        firefox_options.set_preference("browser.cache.offline.enable", False)
        firefox_options.set_preference("network.http.use-cache", False)
        
        # Network timeout settings
        firefox_options.set_preference("network.http.connection-timeout", 300)
        firefox_options.set_preference("network.http.response.timeout", 300)
    else:
        # Non-container mode - use original logic
        if headless:
            firefox_options.add_argument("--headless")
        
        # Platform-specific browser options
        if is_linux:
            # Linux-specific options
            firefox_options.add_argument("--disable-dev-shm-usage")
            firefox_options.add_argument("--no-sandbox")
            firefox_options.add_argument("--disable-gpu")
        elif is_windows:
            # Windows-specific options
            firefox_options.add_argument("--disable-gpu")
        elif is_macos:
            # macOS-specific options
            firefox_options.add_argument("--disable-gpu")
    
    # Common options for all environments
    firefox_options.add_argument("--width=1920")
    firefox_options.add_argument("--height=1080")
    firefox_options.set_preference("browser.download.folderList", 2)
    firefox_options.set_preference("browser.download.dir", os.path.abspath(DOWNLOAD_DIR))
    firefox_options.set_preference("browser.download.useDownloadDir", True)
    firefox_options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/zip,application/octet-stream")
    firefox_options.set_preference("network.cookie.cookieBehavior", 0)
    firefox_options.set_preference("network.cookie.lifetimePolicy", 0)
    firefox_options.set_preference("privacy.trackingprotection.enabled", False)
    firefox_options.set_preference("security.tls.insecure_fallback_hosts", "cyber.mil")
    firefox_options.set_preference("security.tls.unrestricted_rc4_fallback", True)
    firefox_options.set_preference("privacy.resistFingerprinting", False)
    firefox_options.set_preference("browser.safebrowsing.enabled", False)
    firefox_options.set_preference("browser.safebrowsing.malware.enabled", False)
    firefox_options.set_preference("browser.safebrowsing.phishing.enabled", False)
    
    driver = None
    try:
        # Initialize the Firefox driver with webdriver-manager
        try:
            # In containers, try to use pre-installed geckodriver first
            if IS_CONTAINER and os.path.exists("/usr/local/bin/geckodriver"):
                print("Using pre-installed geckodriver in container")
                # Suppress geckodriver logs in containers to reduce noise
                service = Service("/usr/local/bin/geckodriver", log_path='/dev/null')
            else:
                # Use webdriver-manager for automatic download
                service = Service(GeckoDriverManager().install())
        except Exception as e:
            print(f"Error with GeckoDriver: {e}")
            print("\nTroubleshooting tips:")
            print("1. Make sure Firefox is installed")
            if is_macos:
                print("2. On macOS: Firefox should be at /Applications/Firefox.app")
                print("   Or install via: brew install --cask firefox")
                print("3. Try running without headless mode: export STIG_HEADLESS=false")
            elif is_windows:
                print("2. On Windows: Install Firefox from https://www.mozilla.org/firefox/")
                print("3. Default locations: C:\\Program Files\\Mozilla Firefox\\")
                print("4. Try running as Administrator if permission issues occur")
            elif is_linux:
                print("2. On Linux: Install via package manager")
                print("   RHEL/Fedora: sudo dnf install firefox")
                print("   Ubuntu/Debian: sudo apt install firefox")
            raise
        
        print(f"Starting Firefox browser...")
        
        # Platform-specific Firefox binary configuration
        if is_macos:
            firefox_options.set_preference("dom.push.connection.enabled", False)
            # Set Firefox binary location for macOS
            firefox_binary_path = "/Applications/Firefox.app/Contents/MacOS/firefox"
            if os.path.exists(firefox_binary_path):
                firefox_options.binary_location = firefox_binary_path
        elif is_windows:
            # Common Windows Firefox installation paths
            firefox_paths = [
                r"C:\Program Files\Mozilla Firefox\firefox.exe",
                r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Mozilla Firefox\firefox.exe"),
                os.path.expandvars(r"%PROGRAMFILES%\Mozilla Firefox\firefox.exe"),
                os.path.expandvars(r"%PROGRAMFILES(X86)%\Mozilla Firefox\firefox.exe")
            ]
            for path in firefox_paths:
                if os.path.exists(path):
                    firefox_options.binary_location = path
                    print(f"Found Firefox at: {path}")
                    break
            
        # Increase timeout for container environments with retry logic
        max_retries = 3 if IS_CONTAINER else 1
        retry_count = 0
        driver = None
        
        while retry_count < max_retries:
            try:
                if IS_CONTAINER:
                    print(f"Attempting to create Firefox driver (attempt {retry_count + 1}/{max_retries})...")
                    # Set longer timeout for containers
                    driver = webdriver.Firefox(service=service, options=firefox_options)
                    driver.set_page_load_timeout(120)  # Increase to 120 seconds timeout
                    driver.implicitly_wait(20)  # Increase to 20 seconds implicit wait
                else:
                    driver = webdriver.Firefox(service=service, options=firefox_options)
                    driver.set_page_load_timeout(60)  # Standard timeout
                    driver.implicitly_wait(10)  # Standard implicit wait
                print("Firefox driver created successfully")
                break
            except Exception as e:
                retry_count += 1
                print(f"Failed to create driver on attempt {retry_count}: {e}")
                if retry_count < max_retries:
                    print(f"Retrying in 5 seconds...")
                    time.sleep(5)
                else:
                    raise
        
        if not driver:
            raise Exception("Failed to create Firefox driver after all retries")
        
        # Navigate directly to the STIG downloads page
        print("Navigating to STIG downloads page...")
        driver.get(BASE_URL)
        time.sleep(random.uniform(3, 5))
        
        # Verify we successfully accessed the page
        current_url = driver.current_url
        current_title = driver.title
        print(f"Current URL: {current_url}")
        print(f"Page title: {current_title}")
        
        # Wait for the page to load and look for download buttons
        wait = WebDriverWait(driver, 30)
        
        if "BIG-IP logout" in current_title or "logout" in current_title.lower():
            print("Warning: The site appears to be redirecting to a logout page.")
            print("This may indicate that the site is blocking automated access.")
            print("Please try accessing the site manually in a browser to verify it's working.")
            return []
        
        # Wait for page content to load
        try:
            wait.until(lambda driver: driver.find_elements(By.TAG_NAME, "body") and 
                      len(driver.find_elements(By.TAG_NAME, "body")) > 0)
            print("Page content loaded successfully")
        except:
            print("Page content may not have loaded properly")
        
        # Implement pagination to find all STIG.zip files
        # Strategy: The site shows pages 1-10, then clicking » shows 11-20, etc.
        # We will:
        # 1. Click pages 1-10 sequentially
        # 2. When page 10 is done and 11 is not visible, click » to reveal 11-20
        # 3. Click pages 11-20 sequentially
        # 4. Repeat this pattern until all pages are visited
        print("Starting pagination to find all STIG.zip files...")
        print("Pagination strategy: Click numbered pages sequentially, use '»' to reveal next set when needed")
        links = []
        current_page = 1  # Track the actual page number we're on
        pages_processed = 0  # Track total pages processed
        
        # Use the limit if provided, otherwise default to 200
        if max_pages_limit:
            max_pages = max_pages_limit
        else:
            max_pages = 200  # Default maximum
        
        last_button_count = 0
        consecutive_no_new_content = 0
        max_consecutive_no_content = 3
        used_jump_forward = False  # Track if we just used the » button
        
        # Statistics tracking
        total_download_buttons_analyzed = 0
        total_stig_zip_matches = 0
        
        while pages_processed < max_pages:
            pages_processed += 1
            print(f"\n--- Processing iteration {pages_processed}, Current page: {current_page} ---")
            
            # Wait for page to load
            time.sleep(random.uniform(1, 2))
            
            # Find download buttons on current page
            download_buttons = driver.find_elements(By.CLASS_NAME, "downloadButton")
            print(f"Found {len(download_buttons)} download button elements on page {current_page}")
            total_download_buttons_analyzed += len(download_buttons)
            
            # Process download buttons on current page
            stig_links_found_on_page = 0
            current_page_links = []
            for i, button in enumerate(download_buttons):
                data_link = button.get_attribute('data-link')
                if data_link and data_link.endswith('STIG.zip'):
                    current_page_links.append(data_link)
                    total_stig_zip_matches += 1  # Count all STIG.zip matches (including duplicates)
                    if data_link not in links:  # Only add if not already found
                        links.append(data_link)
                        stig_links_found_on_page += 1
                        print(f"  Found NEW STIG.zip: {data_link}")
                    else:
                        print(f"  Found existing STIG.zip: {data_link}")
            
            print(f"Found {stig_links_found_on_page} NEW STIG.zip files on page {current_page}")
            print(f"Total STIG.zip files found so far: {len(links)}")
            print(f"Current page has {len(current_page_links)} STIG.zip links")
            
            # Check if we have more content than before (either more buttons OR new links)
            current_button_count = len(download_buttons)
            new_links_found = stig_links_found_on_page > 0
            
            if current_button_count > last_button_count or new_links_found:
                if current_button_count > last_button_count:
                    print(f"New content loaded! Button count increased from {last_button_count} to {current_button_count}")
                if new_links_found:
                    print(f"New STIG links found! {stig_links_found_on_page} new links on this page")
                last_button_count = current_button_count
                consecutive_no_new_content = 0  # Reset consecutive counter
            else:
                # Only increment if we're not seeing ANY new content AND no buttons are available
                # Don't stop if we still have pages to click through
                page_number_buttons_check = driver.find_elements(By.CSS_SELECTOR, "button.slds-button.slds-button_neutral.slds-button_stretch")
                visible_pages = []
                for btn in page_number_buttons_check:
                    if btn.is_displayed() and btn.is_enabled():
                        btn_text = btn.text.strip()
                        if btn_text.isdigit():
                            visible_pages.append(int(btn_text))
                
                # Check if there are still pages we haven't visited
                unvisited_pages = [p for p in visible_pages if p > current_page]
                
                if unvisited_pages:
                    print(f"No new content on this page, but unvisited pages remain: {unvisited_pages}")
                    consecutive_no_new_content = 0  # Reset since we have more pages to visit
                else:
                    consecutive_no_new_content += 1
                    print(f"No new content loaded and no unvisited pages. Consecutive no content: {consecutive_no_new_content}")
                    
                    # Check if we've reached the end
                    if consecutive_no_new_content >= max_consecutive_no_content:
                        print(f"Reached end of pagination after {consecutive_no_new_content} consecutive pages with no new content")
                        break
            
            # Try scrolling to trigger loading more content
            if consecutive_no_new_content >= 2:
                print("Trying to scroll to trigger loading more content...")
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(random.uniform(2, 3))
                
                # Check if new content appeared
                new_download_buttons = driver.find_elements(By.CLASS_NAME, "downloadButton")
                if len(new_download_buttons) > current_button_count:
                    print(f"Scrolling triggered new content! Button count: {len(new_download_buttons)}")
                    last_button_count = len(new_download_buttons)
                    consecutive_no_new_content = 0
                    continue
                else:
                    print("Scrolling did not trigger new content")
            
            # Look for pagination controls
            try:
                # Look for numbered page buttons (1-9) with the specific class
                page_number_buttons = driver.find_elements(By.CSS_SELECTOR, "button.slds-button.slds-button_neutral.slds-button_stretch")
                
                # Look for the "»" jump forward button
                jump_forward_buttons = driver.find_elements(By.XPATH, "//button[@title='Jump forward 10 pages' and text()='»']")
                if not jump_forward_buttons:
                    # Fallback: look for any button with "»" text
                    jump_forward_buttons = driver.find_elements(By.XPATH, "//button[text()='»']")
                
                # Look for any button with class containing slds-button_neutral
                neutral_buttons = driver.find_elements(By.CSS_SELECTOR, "button.slds-button_neutral")
                
                # Look for "Load More" buttons
                load_more_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Load More') or contains(text(), 'Show More') or contains(text(), 'More') or contains(text(), 'Next')]")
                
                print(f"Found {len(page_number_buttons)} numbered page buttons")
                print(f"Found {len(jump_forward_buttons)} jump forward (») buttons")
                print(f"Found {len(neutral_buttons)} neutral buttons total")
                print(f"Found {len(load_more_buttons)} 'Load More' buttons")
                
                next_button = None
                
                # FIRST PRIORITY: Look for numbered page buttons to click sequentially
                if page_number_buttons:
                    # Get all visible page numbers
                    visible_page_numbers = []
                    for page_btn in page_number_buttons:
                        if page_btn.is_displayed() and page_btn.is_enabled():
                            page_text = page_btn.text.strip()
                            if page_text.isdigit():
                                visible_page_numbers.append((int(page_text), page_btn))
                    
                    # Sort by page number
                    visible_page_numbers.sort(key=lambda x: x[0])
                    
                    if visible_page_numbers:
                        visible_nums = [num for num, _ in visible_page_numbers]
                        min_visible = min(visible_nums)
                        max_visible = max(visible_nums)
                        print(f"Visible page numbers: {visible_nums} (range: {min_visible}-{max_visible})")
                        print(f"Currently on page {current_page}, looking for page {current_page + 1}")
                        
                        # Find the next sequential page to click
                        next_page_found = False
                        for page_num, page_btn in visible_page_numbers:
                            # Click the next page in sequence
                            if page_num == current_page + 1:
                                next_button = page_btn
                                print(f"Selected page {page_num} button (next sequential page)")
                                next_page_found = True
                                break
                        
                        # Special handling: If we're at page 10 and see pages 11-20, continue with page 11
                        # This handles the case where clicking » reveals the next set of pages
                        if not next_button and not next_page_found:
                            # Check if the current page is at the boundary (e.g., 10, 20, 30)
                            # and the visible pages are the next range (e.g., 11-20, 21-30)
                            if min_visible == current_page + 1:
                                # We're at a boundary and the next range is visible
                                for page_num, page_btn in visible_page_numbers:
                                    if page_num == current_page + 1:
                                        next_button = page_btn
                                        print(f"Selected page {page_num} button (continuing to next range)")
                                        break
                        
                        # If we used the jump button and need to determine which page to click
                        if not next_button and used_jump_forward and visible_page_numbers:
                            # After using », we should continue from where we left off
                            # Find the smallest page number that's greater than our current page
                            for page_num, page_btn in visible_page_numbers:
                                if page_num == current_page + 1:
                                    # Found the exact next page
                                    next_button = page_btn
                                    print(f"Selected page {page_num} button (next page after jump)")
                                    break
                                elif page_num > current_page and not next_button:
                                    # Fallback: select the first page greater than current
                                    next_button = page_btn
                                    print(f"Selected page {page_num} button (first available after jump)")
                                    break
                            # Note: we'll reset used_jump_forward after successful click
                
                # SECOND PRIORITY: If no sequential number is available, use the "»" button to get new numbers
                if not next_button and jump_forward_buttons:
                    for btn in jump_forward_buttons:
                        if btn.is_displayed() and btn.is_enabled():
                            next_button = btn
                            print(f"Selected '»' jump forward button (no more sequential numbers available)")
                            used_jump_forward = True  # Mark that we're using the jump button
                            break
                
                # Third priority: Look for "Load More" buttons
                if not next_button and load_more_buttons:
                    for i, btn in enumerate(load_more_buttons):
                        if btn.is_displayed() and btn.is_enabled():
                            btn_text = btn.text.strip()
                            print(f"Load More button {i+1}: text='{btn_text}'")
                            next_button = btn
                            print(f"Selected 'Load More' button as next page button")
                            break
                
                # Fourth priority: Try any neutral button that might be pagination
                if not next_button and neutral_buttons:
                    for i, btn in enumerate(neutral_buttons):
                        if btn.is_displayed() and btn.is_enabled():
                            btn_text = btn.text.strip()
                            btn_title = btn.get_attribute('title') or ''
                            
                            # Skip buttons we've already checked
                            if btn in page_number_buttons or btn in jump_forward_buttons:
                                continue
                                
                            if any(keyword in (btn_text + btn_title).lower() for keyword in ['next', 'forward', 'more', '→', '>']):
                                next_button = btn
                                print(f"Selected neutral button with text '{btn_text}' as next page button")
                                break
                
                if next_button:
                    print(f"Found next page button: '{next_button.text.strip()}' (tag: {next_button.tag_name})")
                    try:
                        # Scroll to the button to make sure it's visible
                        driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                        time.sleep(1)
                        
                        # Store the current number of download buttons before clicking
                        current_button_count = len(download_buttons)
                        print(f"Current download button count: {current_button_count}")
                        
                        # Extract the page number if it's a numbered button
                        clicked_page_number = None
                        button_text = next_button.text.strip()
                        if button_text.isdigit():
                            clicked_page_number = int(button_text)
                        
                        # Try direct button clicking first
                        try:
                            # Scroll to the button and click it directly
                            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", next_button)
                            time.sleep(2)
                            
                            # Try multiple click methods
                            driver.execute_script("arguments[0].click();", next_button)
                            
                            # Wait a bit to see if content loads
                            time.sleep(3)
                            
                            # Check if new content loaded
                            new_download_buttons = driver.find_elements(By.CLASS_NAME, "downloadButton")
                            new_button_count = len(new_download_buttons)
                            
                            # Check for new STIG links
                            new_stig_links = 0
                            for button in new_download_buttons:
                                data_link = button.get_attribute('data-link')
                                if data_link and data_link.endswith('STIG.zip') and data_link not in links:
                                    new_stig_links += 1
                            
                            
                            if new_button_count > current_button_count or new_stig_links > 0:
                                print(f"Direct click worked! Loaded {new_button_count - current_button_count} new download buttons and {new_stig_links} new STIG links")
                                # Update current page if we clicked a numbered button
                                if clicked_page_number:
                                    current_page = clicked_page_number
                                    print(f"Updated current page to {current_page}")
                                    # Reset the jump forward flag if we successfully navigated to a new page
                                    if used_jump_forward:
                                        used_jump_forward = False
                                        print("Reset jump forward flag after successful page navigation")
                                elif used_jump_forward:
                                    # If we used the jump button, we'll determine the new page on the next iteration
                                    print("Used jump forward button, will determine new page on next iteration")
                                continue
                            else:
                                pass  # Will try alternative methods below
                                
                        except Exception as e:
                            pass  # Will try alternative methods below
                        
                        # Try alternative JavaScript click methods
                        try:
                            driver.execute_script("arguments[0].click();", next_button)
                        except:
                            pass
                        
                        try:
                            driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));", next_button)
                        except:
                            pass
                        
                        try:
                            driver.execute_script("arguments[0].focus(); arguments[0].click();", next_button)
                        except:
                            pass
                        
                        # Store the old page before updating (for comparison later)
                        old_page = current_page
                        
                        # Update current page if we clicked a numbered button (important for fallback methods)
                        if clicked_page_number:
                            current_page = clicked_page_number
                        
                        # Wait for dynamic content to load
                        try:
                            # Wait for new download buttons to appear
                            WebDriverWait(driver, 15).until(
                                lambda driver: len(driver.find_elements(By.CLASS_NAME, "downloadButton")) > current_button_count
                            )
                        except:
                            time.sleep(random.uniform(5, 8))
                            
                            # Try scrolling to trigger any lazy loading
                            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                            time.sleep(2)
                            driver.execute_script("window.scrollTo(0, 0);")
                            time.sleep(2)
                        
                        # Check if new content loaded
                        new_download_buttons = driver.find_elements(By.CLASS_NAME, "downloadButton")
                        new_button_count = len(new_download_buttons)
                        
                        # Check if we're navigating to a new page (even if content hasn't changed yet)
                        # Use old_page if it exists (from JavaScript methods), otherwise use current_page
                        comparison_page = old_page if 'old_page' in locals() else current_page
                        page_changed = clicked_page_number and clicked_page_number != comparison_page
                        
                        if new_button_count > current_button_count or page_changed:
                            if new_button_count > current_button_count:
                                print(f"Successfully loaded {new_button_count - current_button_count} new download buttons")
                            elif page_changed:
                                print(f"Page navigation detected: moving from page {comparison_page} to {clicked_page_number}")
                            
                            # Update current page if we clicked a numbered button
                            if clicked_page_number:
                                current_page = clicked_page_number
                                print(f"Updated current page to {current_page}")
                                # Reset the jump forward flag if we successfully navigated to a new page
                                if used_jump_forward:
                                    used_jump_forward = False
                                    print("Reset jump forward flag after successful page navigation")
                            elif used_jump_forward:
                                # If we used the jump button, we'll determine the new page on the next iteration
                                print("Used jump forward button, will determine new page on next iteration")
                            # Continue to the next iteration
                            continue
                        elif new_button_count == current_button_count:
                            print("No new content loaded, reached end of pagination")
                            break
                        else:
                            print("Unexpected: fewer buttons found, might be an error")
                            break
                            
                    except Exception as e:
                        print(f"Error clicking next page button: {e}")
                        break
                else:
                    print("No next page button found")
                    
                    # Try alternative pagination approaches
                    print("Trying alternative pagination approaches...")
                    
                    # Try scrolling to load more content
                    try:
                        print("Attempting scroll-based pagination...")
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(3)
                        driver.execute_script("window.scrollTo(0, 0);")
                        time.sleep(2)
                        
                        # Check if new content appeared
                        new_download_buttons = driver.find_elements(By.CLASS_NAME, "downloadButton")
                        if len(new_download_buttons) > current_button_count:
                            print(f"Scroll-based pagination worked! Button count: {len(new_download_buttons)}")
                            continue
                    except Exception as e:
                        print(f"Scroll-based pagination failed: {e}")
                    
                    # Try looking for "Load More" or "Show More" buttons
                    try:
                        load_more_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Load More') or contains(text(), 'Show More') or contains(text(), 'More') or contains(text(), 'Next')]")
                        if load_more_buttons:
                            print(f"Found {len(load_more_buttons)} 'Load More' buttons")
                            for btn in load_more_buttons:
                                if btn.is_displayed() and btn.is_enabled():
                                    try:
                                        driver.execute_script("arguments[0].click();", btn)
                                        time.sleep(3)
                                        new_download_buttons = driver.find_elements(By.CLASS_NAME, "downloadButton")
                                        if len(new_download_buttons) > current_button_count:
                                            print(f"'Load More' button worked! Button count: {len(new_download_buttons)}")
                                            break
                                    except Exception as e:
                                        print(f"Error clicking 'Load More' button: {e}")
                    except Exception as e:
                        print(f"Error looking for 'Load More' buttons: {e}")
                    
                    # If we haven't found new content for several attempts, we're probably at the end
                    if consecutive_no_new_content >= max_consecutive_no_content:
                        print(f"No new content found for {consecutive_no_new_content} consecutive attempts, reached end of pagination")
                        break
                    else:
                        print("Continuing to look for more content...")
                        continue
                    
            except Exception as e:
                print(f"Error looking for pagination controls: {e}")
                break
        
        print(f"\n=== PAGINATION COMPLETE ===")
        print(f"Total iterations: {pages_processed}")
        print(f"Last page visited: {current_page}")
        print(f"Total STIG.zip files found: {len(links)}")
        print(f"Average STIG files per iteration: {len(links)/pages_processed:.1f}" if pages_processed > 0 else "No pages processed")
        print(f"Pagination stopped due to: {'No more content' if consecutive_no_new_content >= max_consecutive_no_content else 'Maximum iterations reached' if pages_processed >= max_pages else 'Unknown'}")
        print("=" * 50)
        
        # Create absolute URLs and filter for actual zip files
        absolute_links = []
        for link in links:
            if link.startswith('http'):
                absolute_url = link
            else:
                absolute_url = urljoin(BASE_URL, link)
            
            # Only include links that end with STIG.zip
            if absolute_url.endswith('STIG.zip'):
                absolute_links.append(absolute_url)
            else:
                print(f"Filtering out non-STIG.zip link: {absolute_url}")
        
        print(f"Found {len(absolute_links)} .zip file links.")
        
        # Save cookies from the browser session for use with requests
        cookies = driver.get_cookies()
        print(f"Retrieved {len(cookies)} cookies from browser session")
        
        # Return links, cookies, and statistics
        return absolute_links, cookies, pages_processed, total_download_buttons_analyzed, total_stig_zip_matches
        
    except Exception as e:
        print(f"Error: Could not fetch STIG links using Selenium. {e}")
        return [], [], 0, 0, 0
    finally:
        if driver:
            driver.quit()

def download_file(url: str, directory: str, session=None, cookies=None) -> Optional[str]:
    """
    Download a single file from a URL into a specified directory.
    
    Uses the provided session and cookies for authenticated requests. Skips download
    if the file already exists locally. Sanitizes the filename to prevent directory
    traversal attacks.
    
    Args:
        url: The URL of the file to download
        directory: The directory where the file should be saved
        session: Optional requests.Session object for connection pooling (default: None)
        cookies: Optional list of cookie dictionaries from browser session (default: None)
    
    Returns:
        The local file path if download succeeds, None if download fails
    
    Raises:
        requests.exceptions.RequestException: If the download request fails
    """
    # Sanitize filename to prevent directory traversal attacks
    unsafe_filename = url.split('/')[-1]
    safe_filename = sanitize_filename(unsafe_filename)
    local_filename = os.path.join(directory, safe_filename)
    if os.path.exists(local_filename):
        print(f"Skipping {local_filename}, already exists.")
        return local_filename
        
    print(f"Downloading {url}...")
    try:
        # Use session if provided, otherwise create a new one
        if session is None:
            session = requests.Session()
        
        # Use default Python requests headers
        headers = {}
        
        # Add cookies if provided
        if cookies:
            for cookie in cookies:
                session.cookies.set(cookie['name'], cookie['value'], domain=cookie.get('domain', ''))
        
        # Make the request with session
        with session.get(url, stream=True, timeout=30, verify=False, headers=headers, allow_redirects=True) as r:
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"Successfully downloaded {local_filename}")
        return local_filename
    except requests.exceptions.RequestException as e:
        print(f"Error: Failed to download {url}. {e}")
        return None

def process_existing_zips(xslt_transformer) -> Tuple[int, int]:
    """
    Process all existing ZIP files in the download directory without downloading new ones.
    
    Scans the download directory for ZIP files and processes each one, extracting XML
    files and converting them to Markdown using the provided XSLT transformer.
    
    Args:
        xslt_transformer: The XSLT transformation function from lxml.etree.XSLT
    
    Returns:
        A tuple containing:
        - total_xml_files_found: Total number of XML files found in all ZIP files
        - total_xml_files_processed: Total number of XML files successfully converted
    """
    print(f"\n--- Processing Existing ZIP Files ---")
    
    # Find all .zip files in the download directory
    zip_files = []
    if os.path.exists(DOWNLOAD_DIR):
        for file in os.listdir(DOWNLOAD_DIR):
            if file.endswith('.zip'):
                # Sanitize filename to prevent directory traversal
                safe_filename = sanitize_filename(file)
                zip_files.append(os.path.join(DOWNLOAD_DIR, safe_filename))
    
    if not zip_files:
        print(f"No ZIP files found in {DOWNLOAD_DIR}")
        return 0, 0
    
    print(f"Found {len(zip_files)} ZIP files to process")
    
    total_xml_files_found = 0
    total_xml_files_processed = 0
    
    for i, zip_path in enumerate(zip_files, 1):
        print(f"\nProcessing ZIP file {i}/{len(zip_files)}: {os.path.basename(zip_path)}")
        xml_found, xml_processed = process_stig_zip(zip_path, xslt_transformer)
        total_xml_files_found += xml_found
        total_xml_files_processed += xml_processed
    
    return total_xml_files_found, total_xml_files_processed

def process_stig_zip(zip_path: str, xslt_transformer) -> Tuple[int, int]:
    """
    Extract XML files from a ZIP archive and convert them to Markdown.
    
    Opens a ZIP file, finds all XML files (excluding macOS resource forks),
    and converts each one to Markdown format using the provided XSLT transformer.
    Output files are saved to the configured output directory.
    
    Args:
        zip_path: Path to the ZIP file to process
        xslt_transformer: The XSLT transformation function from lxml.etree.XSLT
    
    Returns:
        A tuple containing:
        - xml_files_found: Number of XML files found in the ZIP
        - xml_files_processed: Number of XML files successfully converted to Markdown
    """
    print(f"\nProcessing {zip_path}...")
    xml_files_found = 0
    xml_files_processed = 0
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for file_info in zip_ref.infolist():
                # We only care about .xml files that are not in macOS-specific resource forks
                if file_info.filename.endswith('.xml') and not file_info.filename.startswith('__MACOSX'):
                    print(f"  - Found XML file: {file_info.filename}")
                    xml_files_found += 1
                    
                    # Extract the XML content into memory
                    xml_content = zip_ref.read(file_info.filename)
                    
                    try:
                        # Parse the XML content from memory
                        xml_doc = ET.fromstring(xml_content)
                        
                        # Apply the XSLT transformation
                        markdown_result = xslt_transformer(xml_doc)
                        
                        # Create a clean filename for the output
                        # Sanitize the base filename to prevent directory traversal
                        base_name = os.path.splitext(os.path.basename(file_info.filename))[0]
                        safe_base_name = sanitize_filename(base_name)
                        output_md_path = os.path.join(OUTPUT_DIR, f"{safe_base_name}.md")
                        
                        # Save the transformed content
                        with open(output_md_path, 'w', encoding='utf-8') as f:
                            f.write(str(markdown_result))
                        print(f"    -> Successfully converted to {output_md_path}")
                        xml_files_processed += 1
                        
                    except ET.LxmlError as e:
                        print(f"    -> Error: Could not parse XML file {file_info.filename}. It might not be a valid XCCDF file. {e}")
                    except Exception as e:
                        print(f"    -> Error: An unexpected error occurred during transformation. {e}")

    except zipfile.BadZipFile:
        print(f"Error: {zip_path} is not a valid zip file.")
    except Exception as e:
        print(f"Error: Failed to process {zip_path}. {e}")
    
    return xml_files_found, xml_files_processed


def parse_arguments():
    """
    Parse command-line arguments for the STIG converter.
    
    Defines all available command-line options including scraping limits,
    download options, processing modes, and output verbosity.
    
    Returns:
        argparse.Namespace: Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(
        description='STIG XML to Markdown Converter - Downloads STIG files from cyber.mil and converts them to Markdown',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                     # Full run: scrape all pages, download all, process all
  %(prog)s --test              # Test mode: scrape only 10 pages
  %(prog)s --process-only      # Process existing ZIP files without downloading
  %(prog)s --skip-download     # Scrape links but don't download (useful for testing pagination)
  %(prog)s --max-pages 5       # Limit scraping to 5 pages
  %(prog)s --no-headless       # Run browser in visible mode
  %(prog)s --download-only     # Download files but don't process them
        """
    )
    
    # Scraping options
    parser.add_argument('--test', action='store_true',
                        help='Test mode: limit scraping to 10 pages')
    parser.add_argument('--max-pages', type=int, metavar='N',
                        help='Limit web scraping to N pages')
    parser.add_argument('--skip-scraping', action='store_true',
                        help='Skip web scraping, use existing file list')
    
    # Download options
    parser.add_argument('--skip-download', action='store_true',
                        help='Skip downloading files (useful for testing scraping)')
    parser.add_argument('--download-only', action='store_true',
                        help='Download files but skip XML processing')
    
    # Processing options
    parser.add_argument('--process-only', action='store_true',
                        help='Process existing ZIP files without scraping or downloading')
    parser.add_argument('--skip-existing', action='store_true',
                        help='Skip processing ZIP files that already have output')
    
    # Browser options
    parser.add_argument('--no-headless', action='store_true',
                        help='Run browser in visible mode (same as STIG_HEADLESS=false)')
    
    # Output options
    parser.add_argument('--quiet', action='store_true',
                        help='Minimal output, only show errors and summary')
    parser.add_argument('--verbose', action='store_true',
                        help='Verbose output for debugging')
    
    return parser.parse_args()

def main():
    """
    Main entry point for the STIG downloader and converter.
    
    Orchestrates the complete workflow:
    1. Sets up directories and loads XSLT transformer
    2. Optionally scrapes STIG download links from cyber.mil
    3. Optionally downloads ZIP files
    4. Processes ZIP files to convert XCCDF XML to Markdown
    5. Displays comprehensive statistics about the operation
    
    Exits with code 1 on error, 0 on success.
    """
    args = parse_arguments()
    
    # Handle conflicting arguments
    if args.process_only and (args.skip_download or args.download_only):
        print("Error: --process-only cannot be used with download options")
        sys.exit(1)
    
    if args.skip_download and args.download_only:
        print("Error: --skip-download and --download-only are mutually exclusive")
        sys.exit(1)
    
    print("--- STIG XML to Markdown Converter ---")
    
    # Show environment information
    if IS_CONTAINER:
        print("Running in CONTAINER mode")
        print(f"  Download directory: {DOWNLOAD_DIR}")
        print(f"  Output directory: {OUTPUT_DIR}")
        print(f"  XSLT file: {XSLT_FILE}")
    
    # Apply test mode settings
    if args.test:
        print("Running in TEST MODE (limited to 10 pages)")
        args.max_pages = 10
    
    # 1. Setup
    create_directories()
    
    if not os.path.exists(XSLT_FILE):
        print(f"Error: XSLT stylesheet '{XSLT_FILE}' not found. Please make sure it's in the same directory.")
        return
    
    try:
        xslt_doc = ET.parse(XSLT_FILE)
        xslt_transformer = ET.XSLT(xslt_doc)
    except ET.LxmlError as e:
        print(f"Error: Could not parse the XSLT file. {e}")
        return
    
    # Handle process-only mode
    if args.process_only:
        print("\n--- Process-Only Mode ---")
        print("Skipping web scraping and downloads, processing existing ZIP files...")
        
        total_xml_files_found, total_xml_files_processed = process_existing_zips(xslt_transformer)
        
        print("\n" + "=" * 70)
        print("                    PROCESS-ONLY MODE SUMMARY")
        print("=" * 70)
        print(f"\n📄 XML PROCESSING STATISTICS:")
        print(f"  • XML files found: {total_xml_files_found}")
        print(f"  • XML files successfully converted: {total_xml_files_processed}")
        print(f"  • XML conversion failures: {total_xml_files_found - total_xml_files_processed}")
        if total_xml_files_found > 0:
            print(f"  • XML conversion success rate: {(total_xml_files_processed/total_xml_files_found*100):.1f}%")
        
        print(f"\n✅ FINAL RESULTS:")
        print(f"  • Markdown files created: {total_xml_files_processed}")
        print(f"  • Output directory: '{OUTPUT_DIR}'")
        print("\n" + "=" * 70)
        print("Process Complete!")
        return

    # 2. Get all download links and cookies (unless skip-scraping)
    if not args.skip_scraping:
        print("\nFetching STIG download links from cyber.mil...")
        
        # Check if we should run in headless mode
        headless_mode = not args.no_headless and os.environ.get('STIG_HEADLESS', 'true').lower() != 'false'
        if not headless_mode:
            print("Running in visible browser mode")
        
        result = get_stig_zip_links(headless=headless_mode, max_pages_limit=args.max_pages)
        if not result or not result[0]:  # Check if result is empty or has no links
            print("No STIG files to process.")
            print("\nPossible solutions:")
            print("1. The site may be blocking automated access. Try accessing https://www.cyber.mil/stigs/downloads/ manually in a browser.")
            print("2. The site structure may have changed. Check if the download buttons still have 'downloadButton' class and 'data-link' attributes.")
            print("3. You may need to manually download STIG files and place them in the 'stig_downloads' directory.")
            print("4. Check if there are alternative STIG download sources available.")
            return
        
        # Unpack all the returned values
        zip_links, cookies, pages_processed_stat, buttons_analyzed_stat, stig_matches_stat = result
        if not zip_links:
            print("No STIG files to process.")
            print("\nPossible solutions:")
            print("1. The site may be blocking automated access. Try accessing https://www.cyber.mil/stigs/downloads/ manually in a browser.")
            print("2. The site structure may have changed. Check if the download buttons still have 'downloadButton' class and 'data-link' attributes.")
            print("3. You may need to manually download STIG files and place them in the 'stig_downloads' directory.")
            print("4. Check if there are alternative STIG download sources available.")
            return
    else:
        # Skip scraping mode - no links to download
        print("\n--- Skip Scraping Mode ---")
        print("Skipping web scraping, no links to process")
        return

    # 3. Handle skip-download flag
    if args.skip_download:
        print("\n--- Skipping Downloads (--skip-download flag) ---")
        print(f"Found {len(zip_links)} STIG links but not downloading them")
        print("\n✅ Scraping test complete!")
        return
    
    # 4. Create a session for downloading files
    session = requests.Session()
    
    # 5. Download all zips using the session and cookies
    downloaded_zip_paths = []
    successful_downloads = 0
    failed_downloads = 0
    
    print(f"\n--- Starting Downloads ---")
    print(f"Total files to download: {len(zip_links)}")
    
    for i, link in enumerate(zip_links, 1):
        print(f"\nDownloading file {i}/{len(zip_links)}...")
        path = download_file(link, DOWNLOAD_DIR, session=session, cookies=cookies)
        if path:
            downloaded_zip_paths.append(path)
            successful_downloads += 1
        else:
            failed_downloads += 1
            print(f"  Failed to download: {link}")
        
        # Add a 1 second delay between downloads (except after the last one)
        if i < len(zip_links):
            time.sleep(1)
    
    # Handle download-only flag
    if args.download_only:
        print("\n--- Download-Only Mode Complete ---")
        print(f"Downloaded {successful_downloads} files to '{DOWNLOAD_DIR}'")
        print(f"Failed downloads: {failed_downloads}")
        return
            
    # 6. Process each downloaded zip file
    print(f"\n--- Processing ZIP Files ---")
    print(f"Total ZIP files to process: {len(downloaded_zip_paths)}")
    
    total_xml_files_found = 0
    total_xml_files_processed = 0
    
    for i, zip_path in enumerate(downloaded_zip_paths, 1):
        print(f"\nProcessing ZIP file {i}/{len(downloaded_zip_paths)}...")
        xml_found, xml_processed = process_stig_zip(zip_path, xslt_transformer)
        total_xml_files_found += xml_found
        total_xml_files_processed += xml_processed
    
    # Get the statistics from the scraping phase (need to return them from get_stig_zip_links)
    # For now, we'll use the variables that were set during the process
    
    print("\n" + "=" * 70)
    print("                    FINAL SUMMARY REPORT")
    print("=" * 70)
    
    print("\n📊 SCRAPING STATISTICS:")
    print(f"  • Pages processed: {pages_processed_stat}")
    print(f"  • Download buttons analyzed: {buttons_analyzed_stat}")
    print(f"  • STIG.zip matches found: {stig_matches_stat}")
    print(f"  • Unique STIG.zip links identified: {len(zip_links)}")
    
    print("\n💾 DOWNLOAD STATISTICS:")
    print(f"  • Files attempted to download: {len(zip_links)}")
    print(f"  • Successfully downloaded: {successful_downloads}")
    print(f"  • Failed downloads: {failed_downloads}")
    if len(zip_links) > 0:
        print(f"  • Download success rate: {(successful_downloads/len(zip_links)*100):.1f}%")
    
    print("\n📄 XML PROCESSING STATISTICS:")
    print(f"  • ZIP files processed: {len(downloaded_zip_paths)}")
    print(f"  • XML files found: {total_xml_files_found}")
    print(f"  • XML files successfully converted: {total_xml_files_processed}")
    print(f"  • XML conversion failures: {total_xml_files_found - total_xml_files_processed}")
    if total_xml_files_found > 0:
        print(f"  • XML conversion success rate: {(total_xml_files_processed/total_xml_files_found*100):.1f}%")
    
    print("\n✅ FINAL RESULTS:")
    print(f"  • Markdown files created: {total_xml_files_processed}")
    print(f"  • Output directory: '{OUTPUT_DIR}'")
    
    print("\n" + "=" * 70)
    print("Process Complete!")

if __name__ == "__main__":
    main()