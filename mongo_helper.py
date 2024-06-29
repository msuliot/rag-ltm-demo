from pymongo import MongoClient
from env_config import envs
from datetime import datetime, timezone, timedelta
from bson import ObjectId

env = envs()

class MongoHelper:
    def __init__(self):
        self.client = MongoClient(env.mongo_uri) # mongo cluster uri
        self.db = self.client['ltm'] # ltm is the database name

    def generate_timestamp(self):
        return datetime.now(timezone.utc)

    def has_time_elapsed(self, end_time, minutes):
        if end_time.tzinfo is None:
            saved_timestamp = end_time.replace(tzinfo=timezone.utc)
            
        current_time = self.generate_timestamp()
        time_difference = current_time - saved_timestamp
        return time_difference > timedelta(minutes=minutes)
      
    def total_time_in_conversation(self, start_time):
        # Check if start_time is a string, and if so, convert it to a datetime object
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time)

        # Check if the datetime object is timezone-aware
        if start_time.tzinfo is None:
            saved_timestamp = start_time.replace(tzinfo=timezone.utc)
        else:
            saved_timestamp = start_time

        current_time = self.generate_timestamp()
        time_difference = current_time - saved_timestamp
        formatted_time_difference = str(time_difference).split('.')[0]
        return formatted_time_difference


    # CONVERSATION
    def conversation_delete(self, conversation_id):
        collection = self.db['conversations']
        response = collection.delete_one({"_id": ObjectId(conversation_id)})
        return response


    def conversation_create(self, profile_id):
        collection = self.db['conversations']
        timestamp = self.generate_timestamp()
        new_conversation = {
            "profile_id": profile_id,
            "start_time": timestamp,
            "end_time": "",
            "messages": [],
            "summary": ""
        }
        response = collection.insert_one(
            new_conversation
        )
        return str(response.inserted_id), timestamp.strftime("%Y-%m-%d %H:%M:%S")


    def conversation_update(self, conversation_id, message):
        collection = self.db['conversations']
        timestamp = self.generate_timestamp()
        result = collection.update_one(
            {"_id": ObjectId(conversation_id)},
            {
                "$push": {"messages": message},
                "$set": {
                    "end_time": timestamp, "summary": ""}
            }
        )
        return result


    def remove_empty_conversations(self, minute_threshold):
        collection = self.db['conversations']
        time_delay = self.generate_timestamp() - timedelta(minutes=minute_threshold)
        query = {
            'start_time': {'$lt': time_delay},
            'messages': {'$size': 0}
        }
        result = collection.delete_many(query)
        return result.deleted_count
    
    # PROFILE
    def profile_upsert(self, user_id, first, last, email, phone, city, state, employer, job_title, interests):
        collection = self.db['profiles']
        profile = {
            "user_id": user_id,
            "first_name": first,
            "last_name": last,
            "full_name": f"{first} {last}",
            "email": email,
            "phone": phone,
            "city": city,
            "state": state,
            "employer": employer,
            "job_title": job_title,
            "interests": interests,
            "responses": "short",
            "tone": "friendly",
            "salutation": "first name",
            "created_at": self.generate_timestamp()
        }
        response = collection.update_one(
            {"user_id": user_id},  # Search query to find the user by user_id
            {"$set": profile},     # Update the fields with new values
            upsert=True            # Insert if the user_id does not exist
        )
        if response.upserted_id:
            print(f"Profile created with ID: {response.upserted_id}")
        else:
            print(f"Profile updated for user_id: {user_id}")
        

    def profile_find(self, user_id):
        collection = self.db['profiles']
        profile = collection.find_one({"user_id": user_id})
        return profile
    
    def generate_profile_prompt(self, profile):
        prompt = (
            f"Meet {profile['first_name']} {profile['last_name']}, currently working as "
            f"{profile['job_title']} at {profile['employer']}. Residing in {profile['city']}, "
            f"{profile['state']}, {profile['first_name']} is reachable via email at {profile['email']} "
            f"or phone at {profile['phone']}. They have a keen interest in {profile['interests']}. "
            f"{profile['first_name']} prefers a friendly tone in communication and favors being addressed "
            f"by their first name. Responses are typically short and to the point."
        )
        return prompt


    # CONVERSATION SUMMARY
    def summary_update(self, conversation_id, conversation_summary):
        collection = self.db['conversations']  

        response = collection.update_one(
            {"_id": ObjectId(conversation_id)},
            {"$set": {"summary": conversation_summary}},
            upsert=True
        )

        return response
    

    def summary_find(self, pid):
        ltm = []
        collection = self.db['conversations']
        summaries = collection.find({"profile_id": pid})
        for summary in summaries:
            if summary['summary'] != "":
                ltm.append(summary['summary'])
        return ltm
    
    
    def find_conversation_missing_summary(self):
        collection = self.db['conversations']
        query = {
            '$or': [
                {'summary': {'$exists': False}}, 
                {'summary': ''}
            ],
            'start_time': {'$exists': True, '$type': 'date'},
            'end_time': {'$exists': True, '$type': 'date'}
        }
        conversations = collection.find(query, {'_id': 1, 'end_time': 1, 'messages': 1})
        result = [{'_id': conv['_id'], 'end_time':conv['end_time'], 'messages': conv['messages']} for conv in conversations]
        return result
    
    def get_summary_prompt(self):
        content = """
        Please summarize the provided conversation. Focus on documenting the following aspects:\n
        \n
        Key facts and important information discussed.\n
        Notable outcomes and decisions made.\n
        Any specific details necessary for future reference.\n
        \n
        Ensure the summary does not exceed 1200 characters. Thank you.\n
        \n
        Here is the conversation:\n
        """
        return content