import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "coldchain.db")

def migrate():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        # Verifica se a coluna já existe
        cursor.execute("PRAGMA table_info(devices)")
        columns = [info[1] for info in cursor.fetchall()]
        if "user_id" not in columns:
            print("Adicionando coluna user_id na tabela devices...")
            cursor.execute("ALTER TABLE devices ADD COLUMN user_id INTEGER REFERENCES users(id)")
            
            print("Vinculando freezers existentes ao administrador principal...")
            cursor.execute("UPDATE devices SET user_id = (SELECT id FROM users WHERE email='willian.dantas@admin.com')")
            
            conn.commit()
            print("Migração concluída com sucesso.")
        else:
            print("A coluna user_id já existe na tabela devices.")
    except Exception as e:
        print(f"Erro durante a migração: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
