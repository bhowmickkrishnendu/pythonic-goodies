import wikipediaapi

def search_wikipedia(topic):
    # Create a Wikipedia API object with a custom user agent
    wiki_wiki = wikipediaapi.Wikipedia(
        language='en',
        extract_format=wikipediaapi.ExtractFormat.WIKI,
        user_agent="pythonic-goodies/1.0"
    )

    # Search for the topic
    page = wiki_wiki.page(topic)

    # Check if the page exists
    if page.exists():
        # Get the summary of the page
        summary = page.summary
        print(f"Summary of '{topic}':\n{summary}")
    else:
        print(f"No results found for '{topic}'.")

if __name__ == "__main__":
    topic = input("Enter a topic to search on Wikipedia: ")
    search_wikipedia(topic)
