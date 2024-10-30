import mysql.connector
from mysql.connector import Error
from flask import Flask, request, jsonify
from flask_cors import CORS

# MySQL connection details
host = 'localhost'
port = 3306
user = 'root'
password = 'root'
database_name = 'quiz_db'

app = Flask(__name__)
CORS(app)  # This will enable cross-origin requests from any domain

def create_database():
    connection = None
    try:
        # Connect to MySQL server
        connection = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password
        )
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database_name};")
            print(f"Database '{database_name}' created successfully or already exists.")
    except Error as e:
        print(f"Error while creating database: {e}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def create_tables():
    connection = None
    try:
        # Connect to the MySQL database
        connection = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database_name
        )
        if connection.is_connected():
            cursor = connection.cursor()

            # Create the answers table first to avoid foreign key issues
            create_answers_table_query = '''
            CREATE TABLE IF NOT EXISTS answers (
                answer_id INT AUTO_INCREMENT PRIMARY KEY,
                question_id INT,
                answer_name VARCHAR(255) NOT NULL,
                answer_detail VARCHAR(500)
            );
            '''
            cursor.execute(create_answers_table_query)
            print("'answers' table created successfully or already exists.")

            # Create the questions table
            create_questions_table_query = '''
            CREATE TABLE IF NOT EXISTS questions (
                question_id INT AUTO_INCREMENT PRIMARY KEY,
                question_name VARCHAR(255) NOT NULL,
                right_answer_id INT DEFAULT NULL,
                FOREIGN KEY (right_answer_id) REFERENCES answers(answer_id) ON DELETE SET NULL
            );
            '''
            cursor.execute(create_questions_table_query)
            print("'questions' table created successfully or already exists.")

            # Alter the answers table to add the foreign key constraint if it does not exist
            cursor.execute("SHOW CREATE TABLE answers;")
            create_table_sql = cursor.fetchone()[1]
            if 'fk_question' not in create_table_sql:
                alter_answers_table_query = '''
                ALTER TABLE answers
                ADD CONSTRAINT fk_question
                FOREIGN KEY (question_id) REFERENCES questions(question_id) ON DELETE CASCADE;
                '''
                cursor.execute(alter_answers_table_query)
                print("Foreign key constraint added to 'answers' table successfully.")

    except Error as e:
        print(f"Error while creating tables: {e}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/questions', methods=['GET'])
def get_all_questions():
    try:
        connection = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database_name
        )
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM questions;")
        questions = cursor.fetchall()
        for question in questions:
            cursor.execute("SELECT * FROM answers WHERE question_id = %s;", (question['question_id'],))
            answers = cursor.fetchall()
            question['answers'] = answers
        return jsonify(questions)
    except Error as e:
        return jsonify({'error': str(e)})
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/questions/<int:question_id>', methods=['GET'])
def get_question(question_id):
    try:
        connection = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database_name
        )
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM questions WHERE question_id = %s;", (question_id,))
        question = cursor.fetchone()
        if question:
            cursor.execute("SELECT * FROM answers WHERE question_id = %s;", (question_id,))
            answers = cursor.fetchall()
            question['answers'] = answers
            return jsonify(question)
        else:
            return jsonify({'message': 'Question not found'}), 404
    except Error as e:
        return jsonify({'error': str(e)})
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/questions', methods=['POST'])
def add_question():
    try:
        data = request.get_json()
        question_name = data['question_name']
        answers = data.get('answers', [])
        connection = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database_name
        )
        cursor = connection.cursor()
        cursor.execute("INSERT INTO questions (question_name) VALUES (%s);", (question_name,))
        question_id = cursor.lastrowid
        right_answer_id = None
        
        if len(answers) != 4:
            return jsonify({'error': 'Exactly four options are required for each question'}), 400
        
        correct_answers = [answer for answer in answers if answer.get('is_correct', False)]
        if len(correct_answers) != 1:
            return jsonify({'error': 'Exactly one answer must be marked as correct'}), 400
        
        for answer in answers:
            answer_name = answer['answer_name']
            answer_detail = answer.get('answer_detail') if answer.get('is_correct', False) else None
            cursor.execute(
                "INSERT INTO answers (question_id, answer_name, answer_detail) VALUES (%s, %s, %s);",
                (question_id, answer_name, answer_detail)
            )
            if answer.get('is_correct', False):
                right_answer_id = cursor.lastrowid
        
        # Update the question with the correct answer ID
        cursor.execute("UPDATE questions SET right_answer_id = %s WHERE question_id = %s;", (right_answer_id, question_id))
        
        connection.commit()
        
        return jsonify({'message': 'Question added successfully', 'question_id': question_id}), 201
    except Error as e:
        return jsonify({'error': str(e)})
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/questions/<int:question_id>', methods=['DELETE'])
def delete_question(question_id):
    try:
        connection = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database_name
        )
        cursor = connection.cursor()
        cursor.execute("DELETE FROM questions WHERE question_id = %s;", (question_id,))
        connection.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Question not found'}), 404

        # Reset auto-increment if there are no questions left
        cursor.execute("SELECT COUNT(*) FROM questions;")
        count = cursor.fetchone()[0]
        if count == 0:
            cursor.execute("DELETE FROM answers;")
            connection.commit()
            cursor.execute("ALTER TABLE questions AUTO_INCREMENT = 1;")
            cursor.execute("ALTER TABLE answers AUTO_INCREMENT = 1;")
            connection.commit()

        return jsonify({'message': 'Question deleted successfully'})
    except Error as e:
        return jsonify({'error': str(e)})
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

def main():
    create_database()
    create_tables()
    app.run(host='0.0.0.0', port=5000, debug=True)

if __name__ == '__main__':
    main()
