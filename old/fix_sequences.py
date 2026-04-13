"""
Fix PostgreSQL sequences that are out of sync
This script resets all sequences to the maximum ID + 1
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection

def fix_sequences():
    """Fix all PostgreSQL sequences"""
    with connection.cursor() as cursor:
        # Specifically fix django_admin_log first
        print("Fixing django_admin_log sequence...")
        try:
            cursor.execute("SELECT MAX(id) FROM django_admin_log")
            max_id = cursor.fetchone()[0]
            if max_id is None:
                max_id = 0
            
            cursor.execute("SELECT last_value FROM django_admin_log_id_seq")
            current_value = cursor.fetchone()[0]
            
            new_value = max_id + 1
            cursor.execute(f"SELECT setval('django_admin_log_id_seq', {new_value}, false)")
            print(f"✓ Fixed django_admin_log")
            print(f"  Old sequence value: {current_value}")
            print(f"  Max ID in table: {max_id}")
            print(f"  New sequence value: {new_value}\n")
        except Exception as e:
            print(f"✗ Error fixing django_admin_log: {e}\n")
        
        # Now fix all other sequences
        print("Checking all other sequences...")
        cursor.execute("""
            SELECT sequence_name
            FROM information_schema.sequences
            WHERE sequence_schema = 'public'
            AND sequence_name != 'django_admin_log_id_seq'
        """)
        
        sequences = cursor.fetchall()
        print(f"Found {len(sequences)} sequences to check\n")
        
        for (sequence_name,) in sequences:
            try:
                # Extract table name from sequence name (usually tablename_id_seq)
                table_name = sequence_name.replace('_id_seq', '')
                column_name = 'id'
                
                # Get the maximum ID from the table
                cursor.execute(f'SELECT MAX({column_name}) FROM "{table_name}"')
                result = cursor.fetchone()
                max_id = result[0] if result and result[0] is not None else 0
                
                # Get current sequence value
                cursor.execute(f"SELECT last_value FROM {sequence_name}")
                current_value = cursor.fetchone()[0]
                
                # Set sequence to max_id + 1
                new_value = max_id + 1
                cursor.execute(f"SELECT setval('{sequence_name}', {new_value}, false)")
                
                if current_value < max_id:
                    print(f"✓ Fixed {table_name}")
                    print(f"  Sequence: {sequence_name}")
                    print(f"  Old value: {current_value}, Max ID: {max_id}, New value: {new_value}")
                else:
                    print(f"✓ {table_name} - OK (current: {current_value}, max: {max_id})")
                    
            except Exception as e:
                print(f"✗ Error fixing {sequence_name}: {e}")
        
        print("\n✓ All sequences have been checked and fixed!")

if __name__ == '__main__':
    print("=" * 60)
    print("PostgreSQL Sequence Fix Script")
    print("=" * 60)
    print()
    fix_sequences()
