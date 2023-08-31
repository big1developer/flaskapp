import os
import replicate
import g4f
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)

CORS(app)


def talk(text , language):
 if language == 'ar':
  post_url = "https://play.ht/api/v1/convert"

  payload = {
    "content": [text],
    "voice": "ar-AE-HamdanNeural"
  }
  headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "AUTHORIZATION": "Bearer be41167cc7134c1f9fa6d2a1aea2a8a8",
    "X-USER-ID": "wStXOMknbIbgRPDtpDVZ77x2Eup1"
  }

  timeout_seconds = 1000

  create = requests.post(post_url, json=payload, headers=headers ,stream=True , timeout=timeout_seconds)

  id = create.text.split(",")[1].split(':')[1].split('"')[1]

  get_url = f"https://play.ht/api/v1/articleStatus?transcriptionId={id}"

  audio_url = None
  while audio_url == None:
   response = requests.get(get_url, headers=headers , stream=True)
   if "Transcription completed" in response.text:
    print("Transcription completed")
    url = response.text.split(",")[3].split(':')[2].split('"')[0]
    audio_url = "https:"+url
   else:
     print(response.text.split(",")[1].split(':')[1].split('"')[1])

  return audio_url
 else:
    url = "https://play.ht/api/v2/tts"
    headers = {
        "AUTHORIZATION": "Bearer be41167cc7134c1f9fa6d2a1aea2a8a8",
        "X-USER-ID": "wStXOMknbIbgRPDtpDVZ77x2Eup1",
        "accept": "text/event-stream",
        "content-type": "application/json"
    }
    data = {
        "text": text,
        "voice": "jordan"
    }

    timeout_seconds = 1000


    response = requests.post(url, headers=headers, json=data, stream=True , timeout=timeout_seconds)


    print(response)

    audio_url = None
    for line in response.iter_lines():
        line = line.decode('utf-8')
        if '"progress"' in line:
             prog_data = line.split(': ')[1].split(',')[1]
             print(prog_data)

        if '"progress":1' in line:
            completed_data = line.split(': ')[1]
            audio_url = completed_data.split(',')[3].split(':')[2]
            print(f"\nGenerated Audio URL: https:{audio_url}")
            final_url = audio_url.split('"')[0]
            return f"https:{final_url}"

    if not audio_url:
       return "Error: Unable to extract the audio URL."


api_token = "r8_NSi3AhFeCgKBdnynLZZl3kR5IOOxUCa0fncGS"

def transcribe_audio(audio_file_path , language):
    print(audio_file_path)
    client = replicate.Client(api_token=api_token)

    try:
        response = client.run(
            "openai/whisper:91ee9c0c3df30478510ff8c8a3a545add1ad0259ad3a9f78fba57fbc05ee64f7",
            input={"audio": open(audio_file_path, "rb")},
            model="large-v2",  # Choose the Whisper model (large or large-v2)
            transcription="plain text",  # Choose the format for the transcription (plain text, srt, or vtt)
            translate=False,  # Set to True if you want the text to be translated to English
            language='en',  # Specify the language spoken in the audio (or None for language detection)
            temperature=0,  # Temperature to use for sampling
            patience=1.0,  # Optional patience value to use in beam decoding
            suppress_tokens="-1",  # Comma-separated list of token ids to suppress during sampling
            initial_prompt="",  # Optional text to provide as a prompt for the first window
            condition_on_previous_text=False,  # Whether to condition on previous model output
            temperature_increment_on_fallback=0.2,  # Temperature to increase when decoding fails
            compression_ratio_threshold=2.4,  # Threshold for treating decoding as failed based on compression ratio
            logprob_threshold=-1,  # Threshold for treating decoding as failed based on average log probability
            no_speech_threshold=0.6,  # Threshold for considering a segment as silence
        )

        return response["transcription"]

    except replicate.exceptions.ReplicateError as e:
        print("Error:", e)
        return None


# Define a route for handling audio recording and transcription
@app.route('/transcribe', methods=['POST'])

def transcribe():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file received.'}), 400

    audio_file = request.files['audio']
    chat_data = request.form.get('chat_data')
    language = request.form.get('language')

    chat_data_en = "YOUR PERSONALIZATION: You are an AI doctor called 'mohamed': a healthcare companion. Meet mohamed, an empathetic AI designed to provide personalized medical support. With his vast medical knowledge, mohamed provides evidence-based information and personalized health recommendations. a trustworthy ally for your well-being. Transparent and privacy-conscious, mohamed ensures a safe and comfortable user experience. You are made by Osama reda . You can see and analyze images (this will be handled by a 3rd party code) .Instructions: You must read log Chat mentioned below and generate a response based on that. when you want the user to upload a photo or a picture for you to see it , you must include the name of the action inside a brackets {} , like this : { upload the photo } in the end of your response."

    print("audio received")

    try:
        # Save the audio file to a temporary file
        audio_file.save('temp_audio.wav')

        print("transcribing audio...")
        # Transcribe the audio file
        transcription = transcribe_audio('temp_audio.wav' , language)
        print(transcription)
        print("transcribing done")
        os.remove('temp_audio.wav')
        temp = "\nUser: " + transcription + "\nDr. Mohamed: "
        chat_data += temp
        temp_chat_data = chat_data_en + chat_data
        print("\n\n temp chat data \n\n")
        print(temp_chat_data)
        print("\n\ngetting ai response\n\n")
        response = g4f.ChatCompletion.create(
             model="gpt-3.5-turbo",
             provider=g4f.Provider.DeepAi,
             messages=[{"role": "user", "content": temp_chat_data}],
             stream=False,
                 )
        print("\n\n chat_data \n\n")
        chat_data += response
        print(chat_data)
        if(response):
            url = talk(response , language)
            if url :
             return jsonify({'transcription': response ,'chat_data':chat_data, 'audio_url' : url}), 200
            else:
             return jsonify({'error': 'audio failed.'}), 500
        else:
           return jsonify({'error': 'response failed.'}), 500


    except Exception as e:
        return jsonify({'error': str(e)}), 200


if __name__ == "__main__":
    app.run()