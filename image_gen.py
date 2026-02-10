import urllib

def generate_location_image(prompt_text):
    enhancers = [
        "highly detailed",
        "cinematic lighting",
        "8k resolution",
        "masterpiece",
        "atmospheric",
        "concept art",
        "photorealistic"
    ]
    
    full_prompt = f"{prompt_text}, {', '.join(enhancers)}"

    encoded_prompt = urllib.parse.quote(full_prompt)

    image_url = f"https://pollinations.ai{encoded_prompt}?width=1024&height=1024&nologo=true"

    return image_url