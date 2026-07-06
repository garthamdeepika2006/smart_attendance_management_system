import random
import string
from datetime import datetime, timedelta
from db import get_connection

# generate bluetooth-style token
def generate_token():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


def create_session(teacher_id):
    db = get_connection()
    cursor = db.cursor()

    token = generate_token()
    start_time = datetime.now()
    expiry_time = start_time + timedelta(minutes=3)

    query = """
    INSERT INTO sessions (teacher_id, token, start_time, expiry_time, status)
    VALUES (%s, %s, %s, %s, %s)
    """

    cursor.execute(query, (
        teacher_id,
        token,
        start_time,
        expiry_time,
        "ACTIVE"
    ))

    db.commit()

    print("SESSION CREATED")
    print("TOKEN:", token)
    print("VALID FOR 3 MINUTES")

    return token