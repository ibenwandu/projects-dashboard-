import os
import email
from email import policy
from email.parser import BytesParser
import re
from urllib.parse import urlparse, parse_qs

def extract_text_from_eml(eml_path):
    with open(eml_path, 'rb') as f:
        msg = BytesParser(policy=policy.default).parse(f)
    
    html = None

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == 'text/plain':
                return part.get_content()
            elif content_type == 'text/html':
                html = part.get_content()
    else:
        content_type = msg.get_content_type()
        if content_type == 'text/plain':
            return msg.get_content()
        elif content_type == 'text/html':
            html = msg.get_content()

    if html:
        return re.sub('<[^<]+?>', '', html)
    return ""

def clean_job_link(url):
    """Clean Indeed job links by removing tracking parameters"""
    if 'indeed.com/pagead/clk/dl' in url:
        # Extract the actual job URL from Indeed's tracking link
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        # Try to find the actual job URL in the parameters
        for key, value in query_params.items():
            if key == 'ad' and value:
                # This is the encoded job URL
                return f"https://ca.indeed.com/viewjob?jk={value[0]}"
    
    return url

def extract_job_opportunities(text):
    """Extract job opportunities and clean links"""
    lines = text.splitlines()
    jobs = []
    job_links = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Look for Indeed job links
        if 'indeed.com/pagead/clk/dl' in line:
            clean_url = clean_job_link(line)
            if clean_url not in job_links:
                job_links.append(clean_url)
        
        # Look for job-related content
        elif re.search(r'job|opportunit|position|role|analyst|developer|engineer', line, re.I):
            if line not in jobs and len(line) > 10:  # Avoid very short lines
                jobs.append(line)
    
    return jobs, job_links

def create_job_summary(jobs, job_links):
    """Create a formatted job summary"""
    summary = "🎯 JOB ALERT SUMMARY\n"
    summary += "=" * 50 + "\n\n"
    
    if job_links:
        summary += "📋 JOB OPPORTUNITIES:\n"
        summary += "-" * 30 + "\n"
        for i, link in enumerate(job_links, 1):
            summary += f"{i}. {link}\n"
        summary += "\n"
    
    if jobs:
        summary += "📝 JOB DESCRIPTIONS:\n"
        summary += "-" * 30 + "\n"
        for i, job in enumerate(jobs, 1):
            # Clean up the job description
            clean_job = re.sub(r'https?://[^\s]+', '', job)  # Remove URLs from description
            clean_job = re.sub(r'\s+', ' ', clean_job).strip()  # Clean whitespace
            if clean_job and len(clean_job) > 10:
                summary += f"{i}. {clean_job}\n"
    
    if not jobs and not job_links:
        summary += "❌ No job opportunities found in this email.\n"
    
    summary += "\n" + "=" * 50 + "\n"
    summary += "💡 TIP: Click the links above to view job details on Indeed\n"
    
    return summary

if __name__ == "__main__":
    # Folder containing .eml files
    folder_path = r"C:\Users\user\Desktop\Settling down\Continous Learning\AI\Claude code projects\Emails"
    summary_folder = os.path.join(folder_path, "summaries")

    # Create output folder if it doesn't exist
    os.makedirs(summary_folder, exist_ok=True)

    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".eml"):
            eml_path = os.path.join(folder_path, filename)
            try:
                text = extract_text_from_eml(eml_path)
                jobs, job_links = extract_job_opportunities(text)
                summary = create_job_summary(jobs, job_links)

                # Save summary to file
                summary_filename = os.path.splitext(filename)[0] + "_clean_summary.txt"
                summary_path = os.path.join(summary_folder, summary_filename)
                with open(summary_path, "w", encoding="utf-8") as f:
                    f.write(summary)

                print(f"✅ Processed: {filename}")
                print(f"📊 Found {len(job_links)} job links and {len(jobs)} job descriptions")
            except Exception as e:
                print(f"❌ Error processing {filename}: {e}")
