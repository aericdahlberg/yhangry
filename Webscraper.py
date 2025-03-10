#WebScraper

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time

def scrape_cia_alumni():
    """
    Scrape chef information from CIA Alumni Bios page - or any url alumni page and create a pandas DataFrame.
    Returns a DataFrame with chef details.
    """
    # URL to scrape
    url = "https://www.ciachef.edu/cia-alumni-bios/"
    
    # Send HTTP request to the URL
    print("Fetching page content...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(url, headers=headers)
    
    # Check if the request was successful
    if response.status_code != 200:
        print(f"Failed to retrieve the page. Status code: {response.status_code}")
        return None
    
    # Parse the HTML content
    print("Parsing HTML content...")
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find all alumni bio sections
    # Based on common website structures, each chef profile might be in:
    # - a div with class 'alumnus' 
    # - or in a structured layout with repetitive patterns
    
    # Try to find alumni sections by class
    chef_sections = soup.find_all('div', class_='alumnus')
    
    # If not found, look for other common patterns
    if not chef_sections:
        chef_sections = soup.find_all('div', class_='bio-row')
    
    # If still not found, look for profile card patterns
    if not chef_sections:
        # Try to find repetitive profile structures with images and headings
        # This is a more generic approach
        main_content = soup.find('main') or soup.find(id='main') or soup.find(class_='main-content')
        if main_content:
            # Look for article elements or div elements that might contain profiles
            chef_sections = main_content.find_all('article') or main_content.find_all('div', class_=lambda c: c and ('profile' in c.lower() or 'card' in c.lower() or 'bio' in c.lower()))
    
    print(f"Found {len(chef_sections)} potential chef sections")
    
    # If we still don't have chef sections, try a different approach
    if not chef_sections:
        print("Could not find chef sections using common patterns. Trying alternative approach...")
        # Look for repeated heading patterns that might indicate chef profiles
        headings = soup.find_all('h2')
        chef_sections = []
        for heading in headings:
            # Check if this heading might be a chef name (usually followed by bio content)
            parent = heading.find_parent('div')
            if parent and (parent.find('p') or parent.find('div', class_=lambda c: c and 'content' in c.lower())):
                chef_sections.append(parent)
        print(f"Found {len(chef_sections)} potential chef sections using headings")
    
    # Initialize lists to store chef information
    chef_data = []
    
    # Extract information for each potential chef section
    for i, section in enumerate(chef_sections):
        try:
            # Print progress every 10 chefs
            if i % 10 == 0 and i > 0:
                print(f"Processed {i} chef profiles...")
            
            # Extract chef name - typically in a heading
            name_element = section.find('h2') or section.find('h3')
            name = name_element.text.strip() if name_element else "Unknown"
            
            # Skip if this doesn't look like a chef profile
            if name == "Unknown" or len(name) < 3:
                continue
        
            # Extract chef title/position - might be in h3, h4 or in a div with specific class
            title_element = section.find('h3') or section.find('h4') or section.find('div', class_=lambda c: c and 'title' in c.lower())
            title = title_element.text.strip() if title_element and title_element != name_element else ""
            
            # If title not found, look for strong or b tags
            if not title:
                bold_element = section.find('strong') or section.find('b')
                if bold_element:
                    title = bold_element.text.strip()
            
            # Extract chef bio - typically in paragraphs or a div with content class
            bio = ""
            bio_element = section.find('div', class_=lambda c: c and 'content' in c.lower()) or section
            if bio_element:
                bio_paragraphs = bio_element.find_all('p')
                bio = " ".join([p.text.strip() for p in bio_paragraphs])
            
            # If no paragraphs found, try to get all text
            if not bio and bio_element:
                # Get all text but exclude the name and title
                all_text = bio_element.get_text(separator=' ', strip=True)
                # Remove the name and title from the text if they're present
                if name in all_text:
                    all_text = all_text.replace(name, '', 1)
                if title and title in all_text:
                    all_text = all_text.replace(title, '', 1)
                bio = all_text.strip()
            
            # Extract chef image URL if available
            img_element = section.find('img')
            img_url = ""
            if img_element and 'src' in img_element.attrs:
                img_url = img_element['src']
                # If it's a relative URL, convert to absolute
                if img_url.startswith('/'):
                    img_url = f"https://www.ciachef.edu{img_url}"
            
            # Extract graduation year if present in bio or title
            graduation_year = ""
            # Look for class of YYYY pattern
            year_match = re.search(r'Class of (\d{4})', bio + " " + title)
            if year_match:
                graduation_year = year_match.group(1)
            # If not found, look for any 4-digit year that might be a graduation year
            elif not graduation_year:
                year_match = re.search(r'\b(19\d{2}|20\d{2})\b', bio + " " + title)
                if year_match:
                    graduation_year = year_match.group(1)
            
            # Try to extract restaurant or workplace
            restaurant = ""
            restaurant_patterns = [
                r'at\s+([^,\.]+)',
                r'of\s+([^,\.]+)',
                r'([^,\.]+?)\s+Restaurant',
                r'([^,\.]+?)\s+Bakery',
                r'([^,\.]+?)\s+Café',
                r'([^,\.]+?)\s+Bistro',
                r'([^,\.]+?)\s+Kitchen'
            ]
            
            for pattern in restaurant_patterns:
                restaurant_match = re.search(pattern, title)
                if restaurant_match:
                    restaurant = restaurant_match.group(1).strip()
                    break
            
            # Add chef data to our list if we have sufficient information
            if name != "Unknown" and (title or bio):
                chef_data.append({
                    'Name and Grad Year': name,
                    'Career': bio[:500],  # Limit bio length for readability
                    'Image URL': img_url,
                })
            
            # Be kind to the server - add a small delay between processing
            time.sleep(0.1)
            
        except Exception as e:
            print(f"Error processing chef {i}: {str(e)}")
    
    # Create pandas DataFrame
    print("Creating DataFrame with chef information...")
    df = pd.DataFrame(chef_data)
    
    print(f"Scraping complete. Found information for {len(df)} chefs.")
    return df

def save_to_csv(df, filename="cia_alumni_chefs.csv"):
    """
    Save the DataFrame to a CSV file.
    """
    df.to_csv(filename, index=False, encoding='utf-8')
    print(f"Data saved to {filename}")

def save_to_excel(df, filename="cia_alumni_chefs.xlsx"):
    """
    Save the DataFrame to an Excel file.
    """
    try:
        df.to_excel(filename, index=False)
        print(f"Data saved to {filename}")
    except Exception as e:
        print(f"Error saving to Excel: {str(e)}")
        print("Try installing openpyxl with: pip install openpyxl")

def main():
    # Scrape chef data
    chef_df = scrape_cia_alumni()
    
    if chef_df is not None and not chef_df.empty:
        # Print sample of the data
        print("\n all of chef data:")
        print(chef_df)
        
        # Print statistics
        print("\nDataFrame Info:")
        print(chef_df.info())
        
        # Print potential data quality issues
        print("\nData Quality Check:")
        for col in chef_df.columns:
            missing = chef_df[col].isna().sum()
            if missing > 0:
                print(f"- Column '{col}' has {missing} missing values ({missing/len(chef_df):.1%})")
        
        # Save to CSV
        save_to_csv(chef_df)
        
        # Optionally save to Excel
        save_to_excel(chef_df)
    else:
        print("No chef data was retrieved.")

if __name__ == "__main__":
    main()
