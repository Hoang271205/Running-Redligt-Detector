import mysql.connector
from mysql.connector import Error
import config

class DatabaseManager:
    def __init__(self):
        self.host = config.DB_HOST
        self.user = config.DB_USER
        self.password = config.DB_PASSWORD
        self.database = config.DB_NAME
    
    def get_connection(self):
        """Tạo kết nối database"""
        try:
            connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            return connection
        except Error as e:
            print(f"Database connection error: {e}")
            return None
    
    # utils/database.py - Thay thế toàn bộ hàm create_database_and_table

    def create_database_and_table(self):
        """Tạo database và bảng nếu chưa tồn tại, và đảm bảo cột last_violation tồn tại"""
        connection = None
        try:
            # 1. Kết nối không cần chỉ định database
            connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password
            )
            
            if connection.is_connected():
                cursor = connection.cursor()
                
                # Tạo database
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
                print(f"✓ Database '{self.database}' created/exists")
                
                # Sử dụng database
                cursor.execute(f"USE {self.database}")
                
                # Tạo bảng
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS license_plates (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        plate_number VARCHAR(255) NOT NULL UNIQUE,
                        violation_count INT DEFAULT 1,
                        last_violation TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                """)
                
                # ----------------------------------------------------
                # THÊM LOGIC KIỂM TRA & SỬA CẤU TRÚC BẢNG (ALTER TABLE)
                # ----------------------------------------------------
                
                # Cố gắng thêm cột 'last_violation' phòng trường hợp bảng đã tồn tại 
                # mà không có cột này (do lần chạy trước)
                try:
                    cursor.execute("""
                        ALTER TABLE license_plates 
                        ADD COLUMN last_violation TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;
                    """)
                    print("✓ Column 'last_violation' added (if missing)")
                except Error as alter_e:
                    # Bỏ qua lỗi nếu cột đã tồn tại (MySQL Error Code 1060: Duplicate column name)
                    if alter_e.errno != 1060: 
                        print(f"Warning: Could not check/add column 'last_violation': {alter_e}")
                
                # ----------------------------------------------------

                connection.commit()
                print("✓ Table 'license_plates' created/exists")
                cursor.close()
        
        except Error as e:
            print(f"Error creating database/table: {e}")
        
        finally:
            if connection and connection.is_connected():
                connection.close()
    
    def update_database_with_violation(self, plate_number):
        """Cập nhật vi phạm vào database"""
        try:
            connection = self.get_connection()
            
            if connection and connection.is_connected():
                cursor = connection.cursor()
                
                # Kiểm tra biển số đã tồn tại
                cursor.execute(
                    "SELECT violation_count FROM license_plates WHERE plate_number=%s",
                    (plate_number,)
                )
                result = cursor.fetchone()
                
                if result:
                    # Cập nhật lần vi phạm
                    cursor.execute(
                        "UPDATE license_plates SET violation_count=violation_count+1 WHERE plate_number=%s",
                        (plate_number,)
                    )
                    print(f"  → Updated: {plate_number}")
                else:
                    # Thêm mới
                    cursor.execute(
                        "INSERT INTO license_plates (plate_number) VALUES (%s)",
                        (plate_number,)
                    )
                    print(f"  → Added: {plate_number}")
                
                connection.commit()
                cursor.close()
        
        except Error as e:
            print(f"Error updating database: {e}")
        
        finally:
            if connection and connection.is_connected():
                connection.close()
    
    def get_all_violations(self):
        """Lấy tất cả vi phạm"""
        try:
            connection = self.get_connection()
            
            if connection and connection.is_connected():
                cursor = connection.cursor(dictionary=True)
                
                cursor.execute(
                    "SELECT plate_number, violation_count, last_violation FROM license_plates ORDER BY violation_count DESC"
                )
                result = cursor.fetchall()
                cursor.close()
                
                return result if result else []
        
        except Error as e:
            print(f"Error fetching violations: {e}")
        
        finally:
            if connection and connection.is_connected():
                connection.close()
        
        return []
    
    def clear_license_plates(self):
        """Xóa tất cả vi phạm"""
        try:
            connection = self.get_connection()
            
            if connection and connection.is_connected():
                cursor = connection.cursor()
                cursor.execute("DELETE FROM license_plates")
                connection.commit()
                print("✓ All violations cleared")
                cursor.close()
        
        except Error as e:
            print(f"Error clearing violations: {e}")
        
        finally:
            if connection and connection.is_connected():
                connection.close()