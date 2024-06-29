from mongo_helper import MongoHelper
import os

def main():
    mongo = MongoHelper()
    os.system('clear')  # Clear the screen on MacOS and Linux  

    user_id = input("Enter User ID: ")

    # Default values
    default_profile = {
        "first_name": "First",
        "last_name": "Last",
        "email": "no-email@example.com",
        "phone": "000-000-0000",
        "city": "Unknown City",
        "state": "Unknown State",
        "employer": "Unknown Employer",
        "job_title": "Unknown Job Title",
        "interests": "No specific interests"
    }

    # Get user inputs with defaults
    first_name = input(f"Enter First Name [{default_profile['first_name']}]: ") or default_profile['first_name']
    last_name = input(f"Enter Last Name [{default_profile['last_name']}]: ") or default_profile['last_name']
    email = input(f"Enter Email [{default_profile['email']}]: ") or default_profile['email']
    phone = input(f"Enter Phone [{default_profile['phone']}]: ") or default_profile['phone']
    city = input(f"Enter City [{default_profile['city']}]: ") or default_profile['city']
    state = input(f"Enter State [{default_profile['state']}]: ") or default_profile['state']
    employer = input(f"Enter Employer [{default_profile['employer']}]: ") or default_profile['employer']
    job_title = input(f"Enter Job Title [{default_profile['job_title']}]: ") or default_profile['job_title']
    interests = input(f"Enter Interests [{default_profile['interests']}]: ") or default_profile['interests']

    # Upsert profile
    mongo.profile_upsert(user_id, first_name, last_name, email, phone, city, state, employer, job_title, interests)

if __name__ == "__main__":
    main()