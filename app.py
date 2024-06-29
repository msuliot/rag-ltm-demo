import os
import sys
import json
from colorama import Fore, Style, init # type: ignore snyk
from mongo_helper import MongoHelper
import msuliot.openai_helper as oai # type: ignore snyk # https://github.com/msuliot/package.helpers.git
from msuliot.pinecone_helper import Pinecone # type: ignore snyk # https://github.com/msuliot/package.helpers.git
from msuliot.mongo_helper import MongoDatabase # type: ignore snyk # https://github.com/msuliot/package.helpers.git
from inputimeout import inputimeout, TimeoutOccurred # type: ignore snyk
from datetime import datetime, timezone, timedelta
import sys
import requests

# OpenAI Chat model
model_for_openai_chat = "gpt-4o" 

# Initialize colorama
init()

# Load environment variables
from env_config import envs
env = envs()

# Short Term Memory global variable
stm = []

conversation_start_time = None

# color print functions
def print_green(text):
    print(Fore.GREEN + text + Style.RESET_ALL)

def print_cyan(text):
    print(Fore.CYAN + text + Style.RESET_ALL)

def print_yellow(text):
    print(Fore.YELLOW + text + Style.RESET_ALL)

def print_blue(text):
    print(Fore.BLUE + text + Style.RESET_ALL)

def print_red(text):
    print(Fore.RED + text + Style.RESET_ALL)

def print_magenta(text):
    print(Fore.MAGENTA + text + Style.RESET_ALL)

def display_color(color, text):
    return color + text + Style.RESET_ALL  

# Message functions
def add_to_STM(message):
    global stm
    for m in message:
        stm.append(m)

def create_message(role, content):
    json_message = {
        "role": role, 
        "content": content
    }
    return json_message

# Memory functions
def get_long_term_memory_pinecone(profile,embedding):
    ltm = []
    summaries = query_pinecone_ltm(profile, embedding)

    if summaries:
        message= []
        for summary in summaries:
            message.append(create_message("user", summary))

        for m in message:
            ltm.append(m)

    print_blue(f"Query for Pinecone Long Term Memory similarities for Namespace {str(profile['_id'])}")
    return ltm

def pinecone_ltm(cid, profile, summary):
    oaie = oai.openai_embeddings(env.openai_key, "text-embedding-3-small")
    values = oaie.execute(summary)

    pinecone_objects = []

    pinecone_object = {
            "id": cid,
            "values": values.data[0].embedding,
            "metadata": {
                # "profile_id": str(profile['_id']),
                "summary": summary,
                "timestamp": datetime.now(timezone.utc)
            }
        }

    pinecone_objects.append(pinecone_object)

    pc = Pinecone(api_key=env.pinecone_key)
    try:
        index = pc.Index('hippocampus')
    except:
        print("error creating index")

    results = index.upsert(vectors=pinecone_objects, namespace=str(profile['_id']))
    print_blue(f"Save conversation summary to LTM in Pinecone for namespace {profile['_id']} with Conversation ID {cid}")
    return results

def save_short_term_memory(message):
    add_to_STM(message)
    print_blue("\nSave Question and Answer to Short Term Memory")

# simulate login
def login():
    uid = input("Please enter your User ID: ")
    if not uid:
        return
    print_blue(f"Validating User ID {uid}")
    return uid

# Converstion functions
def conversation_end(mongo, cid, profile):
    global conversation_start_time
    print(f"Thank you, Have a great day?")
    print_blue(f"End: Conversation ID: {cid}")
    
    if not stm:
        print_blue("Short Term Memory is empty, removing temporary conversation")
        mongo.conversation_delete(cid)
        return
    else:
        the_summary = create_conversation_summary(mongo, cid, profile)
        # TODO:  change LTM to Pinecone Vector Database
        # mongo.summary_update(cid, the_summary)
        results = pinecone_ltm(cid, profile, the_summary)

    total_conversation_time = mongo.total_time_in_conversation(conversation_start_time)
    print_blue(f"Total conversation time: {total_conversation_time}")

def create_conversation_summary(mongo, cid, profile):
    # print_blue(f"Save conversation summary to LTM in MongoDB for {profile['user_id']} with Conversation ID: {cid}")
    oaic = oai.openai_chat(env.openai_key, model_for_openai_chat)

    content = mongo.get_summary_prompt() + json.dumps(stm, indent=2)
    
    oaic.add_message("user", content)
    response = oaic.execute()
    print_blue(f"Conversation summary of {len(response)} characters was added to LTM for conversation ID: {cid}")
    return response

# Greeting functions and question
def initial_greeting(profile):
    print(f"Welcome to the RAG AI Chatbot, {profile["first_name"]}! How can I help you today?")

def get_question(timeout): 
    try:
        question = inputimeout(prompt="question:> ", timeout=timeout)
    except TimeoutOccurred:
        print_red(f"There has been no activity for {timeout} seconds. This conversation is ending.")
        question = "exit"
    return question

def source_ref(response_pine):
    pine_source = []
    desired_length = 43
    for info in response_pine:
        source_loc = info['source']
        if len(source_loc) > desired_length:
            shortened_path = "..." + source_loc[-(desired_length - 3):]
        else:
            shortened_path = source_loc
        pine_source.append(f"Source: {shortened_path} Score: {info['score']} Chunk: {info['chunk_number']}")
    return pine_source

# OpenAI Chat functions
def get_chat_completion_messages(conbine_message):

    oaic = oai.openai_chat(env.openai_key, model_for_openai_chat)
    oaic.add_message("system", "you are an AI system created to answer questions accurately, and precise. Try to keep responses to 500 characters.")
    for m in conbine_message:
        oaic.add_message(m["role"], m["content"])

    response = oaic.execute_stream() 
    # print_blue("Received a response from ChatGPT after sending the Profile, Long-Term Memory, Short-Term Memory, Pinecone content, and the question.")
    return response

# RAG - Pinecone prompt
def create_prompt(query, content):
    prompt_start = ("Answer the question based only on the content provided.\n\n" + "Context:\n") 
    prompt_end = (f"\n\nQuestion: {query}")
    data = []
    for info in content:
        data.append(f"Source: {info['source']}\nContent: {info['content']}\nScore: {info['score']}")

    prompt = (prompt_start + "\n\n---\n\n".join(data) + prompt_end)
    return prompt

def embed_text(text):
    model_for_openai_embedding = "text-embedding-3-small"
    oaie = oai.openai_embeddings(env.openai_key, model_for_openai_embedding)
    embed = oaie.execute(text)  
    print_blue("Created an embedding for the question using ChatGPT.")
    return embed

def query_pinecone(embedding):
    namespace = "ltm"
    database = "blades-of-grass"
    pc = Pinecone(api_key=env.pinecone_key)
    index = pc.Index(database)

    # Query Pinecone Index
    response_pine = index.query(
        namespace=namespace,
        vector=embedding.data[0].embedding, 
        top_k=5, 
        include_metadata=True, 
        include_values=False,
    )
 
    source_files = []
    source_info = []

    # Process matches from Pinecone response
    for match in response_pine['matches']:
        chunk_id = match['id']
        source_file = match['metadata']['source']
        chunk_number = match['metadata']['chunk_number']
        score = match['score']

        source_files.append(f"{source_file} - {chunk_number} - {score}")

        # Retrieve chunk text from MongoDB
        with MongoDatabase(env.mongo_uri) as client:
            chunk_text = client.get_document_by_chunk_id(database, namespace, chunk_id)
            text = chunk_text[0]['data'][0]['text']
            # content.append(f"SourceFile: {source_file}, Content: {text}")
            
            # Store source file name and text content in source_info
            source_info.append({
                'source': source_file,
                'chunk_number': chunk_number,
                'score': score,
                'content': text
            })

    print_blue(f"Query for Pinecone content based on embedding. Found {len(source_files)} matches.")
    return source_info

def query_pinecone_ltm(profile, embedding):
    database = "hippocampus"
    namespace = str(profile['_id'])
    pc = Pinecone(api_key=env.pinecone_key)
    index = pc.Index(database)

    # Query Pinecone Index
    response_pine = index.query(
        namespace=namespace,
        vector=embedding.data[0].embedding, 
        top_k=3, 
        include_metadata=True, 
        include_values=False,
    )
 
    source_info = []

    # Process matches from Pinecone response
    for match in response_pine['matches']:
        summary = match['metadata']['summary']
        source_info.append(summary)

    return source_info

# Main function
def main():
    global stm, conversation_start_time
    pinecone_source = []
    mongo = MongoHelper()
    os.system('clear') # Clear the screen on MacOS and Linux

    # Simulate Login
    uid = login()
    if not uid:
        print_red("User ID is required")
        sys.exit()

    # Get user profile
    profile = mongo.profile_find(uid)
    if not profile:
        print_red(f"Profile not found for {uid}")
        sys.exit()

    profile_prompt = mongo.generate_profile_prompt(profile)
    profile_id = str(profile['_id'])
    print_blue(f"Profile ID: {profile_id}")
    profile_memory = []
    profile_memory.append(create_message("user", profile_prompt))

    # Greet user
    initial_greeting(profile)
    
    # long term memory 
    ltm = []

    # Start conversation
    conversation_id, conversation_start_time = mongo.conversation_create(profile_id)
    print_blue(f"Conversation started at {conversation_start_time} UTC with Conversation ID: {conversation_id} in MongoDB")
    
    # Set timeout for no activity in seconds to end the conversation
    no_activity_timeout = 600 # in seconds

    # Main loop to get user questions and provide answers
    while True:
        message = []
        question = get_question(no_activity_timeout) # seconds for timeout

        if question.lower() in ("exit", "quit", "bye", "end", "done", "thanks"):
            conversation_end(mongo, conversation_id, profile)
            break
        if question.lower() == "profile":
            pretty_json = json.dumps(profile_memory, indent=2)
            print(pretty_json)
            continue
        if question.lower() == "ltm":
            pretty_json = json.dumps(ltm, indent=2)
            print(pretty_json)
            continue
        if question.lower() == "stm":
            pretty_json = json.dumps(stm, indent=2)
            print(pretty_json)
            continue
        if question.lower() in ("source", "sources"):
            pretty_json = json.dumps(pinecone_source, indent=2)
            print(pretty_json)
            continue
        
        message.append(create_message("user", question))
        
        # Get embedding for question
        embedding = embed_text(question)

        # Get long term memory based on embedded question
        ltm = get_long_term_memory_pinecone(profile, embedding)

        # Get Pinecone content based on embedded question
        response_pine = query_pinecone(embedding)
        pinecone_source = source_ref(response_pine)
        prompt_rag = create_prompt(question, response_pine)
        pine = []
        pine.append(create_message("user", prompt_rag)) # This contains the question and the content from the Rag - Pinecone

        # Combine all messages for the chat model
        combine_message = profile_memory + ltm + stm + pine
        response = get_chat_completion_messages(combine_message)
        message.append(create_message("assistant", response))

        save_short_term_memory(message)
        
        # Save to MongoDB
        mongo.conversation_update(conversation_id, create_message("user", question))
        mongo.conversation_update(conversation_id, create_message("assistant", response))
        print_blue(f"Save Question and Answer to Conversation {conversation_id} in MongoDB")

if __name__ == "__main__":
    main()