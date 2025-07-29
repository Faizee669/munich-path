import os
import random

# Try to import Gemini, but make it optional
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("Warning: google-generativeai package not found. AI features will be disabled.")

# Define default exercises as a fallback
DEFAULT_EXERCISES = {
    "A1": [
        "What is 'Guten Morgen' in English?",
        "Conjugate the verb 'sein' (to be) for 'Ich', 'Du', and 'Er/Sie/Es'.",
        "Translate: 'My name is [Your Name]. I am from [Your Country].'",
    ],
    "A2": [
        "Describe your typical workday in 2-3 German sentences.",
        "Form a sentence using a Dative case preposition (e.g., mit, nach, von).",
        "Translate: 'I would like to order a coffee and a croissant, please.'"
    ],
    "B1": [
        "Explain the difference between 'man' and 'jemand' in German, with examples.",
        "Write a short email to a potential employer expressing your interest in a job.",
        "Translate: 'Although it was raining, we decided to go for a walk in the park.'"
    ],
    "B2": [
        "Discuss the pros and cons of digitalization in the workplace (2-3 sentences).",
        "Form a sentence using a subjunctive II construction (Konjunktiv II).",
        "Translate: 'It is important that we consider all aspects before making a decision.'"
    ],
    "C1": [
        "Analyze a recent news headline from a German newspaper and summarize its implications.",
        "Explain the nuanced usage of a modal particle like 'doch' or 'mal' in conversation.",
        "Write a paragraph about an aspect of German culture that fascinates you, using complex sentence structures."
    ],
    "C2": [
        "Critically evaluate the current political climate in Germany, citing specific policies or events.",
        "Debate the merits of traditional vs. modern approaches to language learning.",
        "Compose a short narrative or descriptive piece about a personal experience in Germany, demonstrating advanced vocabulary and idiomatic expressions."
    ]
}


def configure_gemini(api_key):
    """
    Configures the Gemini API with the provided API key and tests a model.
    Checks for available models and sets a working one in session state.
    Args:
        api_key (str): The Google Gemini API key.
    Returns:
        bool: True if configuration is successful, False otherwise.
    """
    if not GEMINI_AVAILABLE:
        print("Gemini package not available. Skipping configuration.")
        return False
    if not api_key:
        print("Gemini API key is missing. Cannot configure.")
        return False

    try:
        genai.configure(api_key=api_key)
        
        # Prioritize models that are generally good for content generation
        # Ordered by preference, from newest/most capable to older/lighter
        model_names_preference = [
            'gemini-1.5-flash',
            'gemini-1.5-pro',
            'gemini-pro-latest',
            'gemini-pro',
        ]
        
        for model_name in model_names_preference:
            try:
                # Attempt to get model and make a test call
                model = genai.GenerativeModel(model_name)
                # Small, simple prompt to test connectivity and functionality
                response = model.generate_content("Hello")
                # If no error, model is likely configured and working
                print(f"Successfully configured Gemini with model: {model_name}")
                # In a Streamlit app, you might update st.session_state here
                # For this service layer, we just return True
                return True
            except Exception as model_error:
                # print(f"Could not use model {model_name}: {model_error}")
                continue # Try the next model in the preference list
        
        print("No working Gemini model could be configured with the provided API key.")
        # Optionally list available models for more detailed error reporting
        # try:
        #     models = genai.list_models()
        #     available_models = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
        #     print(f"Available models with generateContent capability: {available_models}")
        # except Exception as e:
        #     print(f"Could not list available Gemini models: {e}")
        
        return False
    except Exception as e:
        print(f"Gemini global configuration failed: {e}")
        return False

def generate_german_exercises(current_level, api_key, focus_area="vocabulary"):
    """
    Generates personalized German exercises using Gemini AI, or returns defaults if AI fails.
    Args:
        current_level (str): The CEFR level (e.g., "A1", "B2").
        api_key (str): The Google Gemini API key.
        focus_area (str): The specific area for exercises (e.g., "vocabulary", "grammar").
    Returns:
        list: A list of 3 German exercises (strings).
    """
    if not GEMINI_AVAILABLE or not api_key:
        print("Gemini not available or API key missing. Returning default exercises.")
        return DEFAULT_EXERCISES.get(current_level, DEFAULT_EXERCISES["A1"])

    try:
        # Ensure Gemini is configured for this call if it wasn't already
        # In a real app, you'd likely configure once globally or per user session.
        # This call makes it robust for individual function calls.
        if not configure_gemini(api_key):
             print("Gemini configuration failed within generate_german_exercises. Returning defaults.")
             return DEFAULT_EXERCISES.get(current_level, DEFAULT_EXERCISES["A1"])

        # Determine the model to use (assuming configure_gemini would set a preferred one,
        # or you pick a default here if multiple are configured)
        model = genai.GenerativeModel('gemini-1.5-flash') # Or use a model name stored in session state if passed

        prompt = f"""
        Generate exactly 3 German learning exercises for {current_level} level focusing on {focus_area}.
        Make the exercises practical and engaging for someone preparing to work in Munich.
        
        Format your response as a numbered list like this:
        1. [Question 1]
        2. [Question 2]
        3. [Question 3]
        
        Level: {current_level}
        Focus: {focus_area}
        Context: Professional preparation for Munich, including topics like work, daily life, integration.
        """
        
        response = model.generate_content(prompt)
        exercises_text = response.text.strip()
        
        exercises = []
        # Split by newline and filter for lines starting with 'X.'
        lines = exercises_text.split('\n')
        for line in lines:
            line = line.strip()
            if line and line.startswith(('1.', '2.', '3.')):
                exercise = line[line.find('.') + 1:].strip() # Remove "1.", "2.", "3." prefix
                if exercise:
                    exercises.append(exercise)
        
        if len(exercises) < 3: # Fallback if AI doesn't return enough exercises
            print(f"AI returned fewer than 3 exercises. Falling back to defaults. AI response:\n{exercises_text}")
            return DEFAULT_EXERCISES.get(current_level, DEFAULT_EXERCISES["A1"])
        
        return exercises[:3] # Ensure exactly 3 are returned
        
    except Exception as e:
        print(f"Error generating exercises via AI: {e}. Returning default exercises.")
        return DEFAULT_EXERCISES.get(current_level, DEFAULT_EXERCISES["A1"])

