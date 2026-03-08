import webbrowser
import re
import time

def extract_job_links_from_summary(summary_file_path):
    """Extract job links from the summary file"""
    job_links = []
    
    try:
        with open(summary_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Find all Indeed job links
        links = re.findall(r'https://ca\.indeed\.com/viewjob\?jk=[^\s]+', content)
        job_links.extend(links)
        
    except FileNotFoundError:
        print(f"❌ Summary file not found: {summary_file_path}")
        return []
    except Exception as e:
        print(f"❌ Error reading summary file: {e}")
        return []
    
    return job_links

def open_job_links(job_links, delay=2):
    """Open job links in browser with a delay between each"""
    if not job_links:
        print("❌ No job links found to open.")
        return
    
    print(f"🚀 Opening {len(job_links)} job opportunities in your browser...")
    print("⏳ There will be a {delay}-second delay between each link to avoid overwhelming your browser.\n")
    
    for i, link in enumerate(job_links, 1):
        print(f"📋 Opening job {i}/{len(job_links)}: {link}")
        try:
            webbrowser.open(link)
            if i < len(job_links):  # Don't delay after the last link
                print(f"⏳ Waiting {delay} seconds before next job...")
                time.sleep(delay)
        except Exception as e:
            print(f"❌ Error opening link {i}: {e}")
    
    print(f"\n✅ All {len(job_links)} job links have been opened!")

if __name__ == "__main__":
    # Path to the summary file
    summary_file = r"C:\Users\user\Desktop\Settling down\Continous Learning\AI\Claude code projects\Emails\summaries\Business Analyst at UMI Group Inc. in Guelph, ON and 5 more new jobs_clean_summary.txt"
    
    # Extract job links
    job_links = extract_job_links_from_summary(summary_file)
    
    if job_links:
        print(f"🎯 Found {len(job_links)} job opportunities:")
        for i, link in enumerate(job_links, 1):
            print(f"  {i}. {link}")
        
        print(f"\n💡 Would you like to open all {len(job_links)} job links in your browser?")
        print("   This will open each job posting in a new tab with a 2-second delay between each.")
        
        # Ask for confirmation
        response = input("\nOpen all job links? (y/n): ").lower().strip()
        
        if response in ['y', 'yes', '']:
            open_job_links(job_links)
        else:
            print("❌ Job links not opened.")
    else:
        print("❌ No job links found in the summary file.") 