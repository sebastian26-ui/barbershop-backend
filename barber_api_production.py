#!/usr/bin/env python3
"""
Production Barbershop API with PostgreSQL support
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import hashlib
import uuid
from datetime import datetime, timedelta
from urllib.parse import urlparse

# Determine if we're in production or development
DATABASE_URL = os.environ.get('DATABASE_URL')
IS_PRODUCTION = DATABASE_URL is not None

if IS_PRODUCTION:
    # Production: Use PostgreSQL
    import psycopg2
    from psycopg2.extras import RealDictCursor
    # Fix for Render.com: postgres:// → postgresql://
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
else:
    # Development: Use SQLite
    import sqlite3
    DB_PATH = 'reservations.db'

app = Flask(__name__)

# CORS Configuration - Allow all origins for deployment
# This allows GitHub Pages, Netlify, and any other frontend
CORS(app, 
     resources={r"/api/*": {"origins": "*"}},
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
     expose_headers=["Content-Type"],
     supports_credentials=False)

# Test mode (allow any email to login)
TEST_MODE = os.environ.get('TEST_MODE', 'true').lower() == 'true'

def get_db_connection():
    """Get database connection (PostgreSQL or SQLite)"""
    if IS_PRODUCTION:
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

def init_database():
    """Initialize database with required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if IS_PRODUCTION:
        # PostgreSQL schema
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS barbers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT,
                phone TEXT,
                bio TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS services (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                price REAL,
                duration_minutes INTEGER,
                category TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS barber_availability (
                id TEXT PRIMARY KEY,
                barber_id TEXT NOT NULL,
                day_of_week INTEGER,
                specific_date TEXT,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                is_available INTEGER DEFAULT 1,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (barber_id) REFERENCES barbers(id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS barber_services (
                barber_id TEXT NOT NULL,
                service_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (barber_id, service_id),
                FOREIGN KEY (barber_id) REFERENCES barbers(id) ON DELETE CASCADE,
                FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reservations (
                id TEXT PRIMARY KEY,
                customer_name TEXT NOT NULL,
                customer_email TEXT,
                customer_phone TEXT,
                service_id TEXT NOT NULL,
                barber_id TEXT NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                status TEXT DEFAULT 'PENDING',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (service_id) REFERENCES services(id),
                FOREIGN KEY (barber_id) REFERENCES barbers(id)
            )
        ''')
        
        # Insert default services
        default_services = [
            ('corte-clasico', 'Corte Clásico', 'Corte tradicional con tijera y máquina', 15000, 30, 'clasico'),
            ('fade', 'Fade', 'Degradado moderno y preciso', 18000, 45, 'premium'),
            ('barba', 'Arreglo de Barba', 'Perfilado y arreglo completo', 12000, 20, 'clasico'),
            ('corte-barba', 'Corte + Barba', 'Servicio completo', 25000, 50, 'premium'),
        ]
        
        for service in default_services:
            cursor.execute('''
                INSERT INTO services (id, name, description, price, duration_minutes, category)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (name) DO NOTHING
            ''', service)
    
    else:
        # SQLite schema (same as before)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS barbers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT,
                phone TEXT,
                bio TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS services (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                price REAL,
                duration_minutes INTEGER,
                category TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS barber_availability (
                id TEXT PRIMARY KEY,
                barber_id TEXT NOT NULL,
                day_of_week INTEGER,
                specific_date TEXT,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                is_available INTEGER DEFAULT 1,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (barber_id) REFERENCES barbers(id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS barber_services (
                barber_id TEXT NOT NULL,
                service_id TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (barber_id, service_id),
                FOREIGN KEY (barber_id) REFERENCES barbers(id) ON DELETE CASCADE,
                FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reservations (
                id TEXT PRIMARY KEY,
                customer_name TEXT NOT NULL,
                customer_email TEXT,
                customer_phone TEXT,
                service_id TEXT NOT NULL,
                barber_id TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                status TEXT DEFAULT 'PENDING',
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (service_id) REFERENCES services(id),
                FOREIGN KEY (barber_id) REFERENCES barbers(id)
            )
        ''')
        
        # Insert default services
        default_services = [
            ('corte-clasico', 'Corte Clásico', 'Corte tradicional con tijera y máquina', 15000, 30, 'clasico'),
            ('fade', 'Fade', 'Degradado moderno y preciso', 18000, 45, 'premium'),
            ('barba', 'Arreglo de Barba', 'Perfilado y arreglo completo', 12000, 20, 'clasico'),
            ('corte-barba', 'Corte + Barba', 'Servicio completo', 25000, 50, 'premium'),
        ]
        
        for service in default_services:
            cursor.execute('''
                INSERT OR IGNORE INTO services (id, name, description, price, duration_minutes, category)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', service)
    
    conn.commit()
    conn.close()
    print(f"✅ Database initialized ({'PostgreSQL' if IS_PRODUCTION else 'SQLite'})")

def hash_password(password):
    """Simple password hashing"""
    return hashlib.sha256(password.encode()).hexdigest()

# Initialize database on startup
init_database()

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/api/services', methods=['GET'])
def get_services():
    """Get all active services"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if IS_PRODUCTION:
        cursor.execute('SELECT * FROM services WHERE is_active = 1 ORDER BY name')
    else:
        cursor.execute('SELECT * FROM services WHERE is_active = 1 ORDER BY name')
    
    services = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({'services': services})

@app.route('/api/barbers', methods=['GET'])
def get_barbers():
    """Get all active barbers"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, name, bio, phone FROM barbers WHERE is_active = 1 ORDER BY name')
    barbers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({'barbers': barbers})

@app.route('/api/auth/login', methods=['POST'])
def barber_login():
    """Barber authentication"""
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if IS_PRODUCTION:
        cursor.execute('SELECT * FROM barbers WHERE email = %s AND is_active = 1', (email,))
    else:
        cursor.execute('SELECT * FROM barbers WHERE email = ? AND is_active = 1', (email,))
    
    barber = cursor.fetchone()
    
    if TEST_MODE and not barber:
        # Create new barber in test mode
        barber_id = str(uuid.uuid4())
        name = email.split('@')[0].title()
        
        if IS_PRODUCTION:
            cursor.execute('''
                INSERT INTO barbers (id, name, email, password_hash, is_active)
                VALUES (%s, %s, %s, %s, 1)
            ''', (barber_id, name, email, hash_password(password)))
        else:
            cursor.execute('''
                INSERT INTO barbers (id, name, email, password_hash, is_active)
                VALUES (?, ?, ?, ?, 1)
            ''', (barber_id, name, email, hash_password(password)))
        
        conn.commit()
        
        if IS_PRODUCTION:
            cursor.execute('SELECT * FROM barbers WHERE id = %s', (barber_id,))
        else:
            cursor.execute('SELECT * FROM barbers WHERE id = ?', (barber_id,))
        
        barber = cursor.fetchone()
    
    conn.close()
    
    if barber:
        return jsonify({
            'success': True,
            'barber': {
                'id': barber['id'],
                'name': barber['name'],
                'email': barber['email']
            }
        })
    
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/barber/<barber_id>/services', methods=['GET', 'POST'])
def barber_services(barber_id):
    """Get or save barber's services"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'GET':
        if IS_PRODUCTION:
            cursor.execute('''
                SELECT s.id, s.name, s.description, s.price, s.duration_minutes
                FROM services s
                INNER JOIN barber_services bs ON s.id = bs.service_id
                WHERE bs.barber_id = %s
                ORDER BY s.name
            ''', (barber_id,))
        else:
            cursor.execute('''
                SELECT s.id, s.name, s.description, s.price, s.duration_minutes
                FROM services s
                INNER JOIN barber_services bs ON s.id = bs.service_id
                WHERE bs.barber_id = ?
                ORDER BY s.name
            ''', (barber_id,))
        
        services = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify({'services': services})
    
    elif request.method == 'POST':
        data = request.json
        service_ids = data.get('serviceIds', [])
        
        # Delete existing services
        if IS_PRODUCTION:
            cursor.execute('DELETE FROM barber_services WHERE barber_id = %s', (barber_id,))
            
            # Insert new services
            for service_id in service_ids:
                cursor.execute('''
                    INSERT INTO barber_services (barber_id, service_id)
                    VALUES (%s, %s)
                ''', (barber_id, service_id))
        else:
            cursor.execute('DELETE FROM barber_services WHERE barber_id = ?', (barber_id,))
            
            # Insert new services
            for service_id in service_ids:
                cursor.execute('''
                    INSERT INTO barber_services (barber_id, service_id)
                    VALUES (?, ?)
                ''', (barber_id, service_id))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Services saved successfully'}), 201

@app.route('/api/barber/<barber_id>/availability', methods=['GET', 'POST'])
def barber_availability(barber_id):
    """Get or add barber availability"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'GET':
        if IS_PRODUCTION:
            cursor.execute('''
                SELECT id, day_of_week, specific_date, start_time, end_time, is_available
                FROM barber_availability
                WHERE barber_id = %s AND is_active = 1
                ORDER BY 
                    CASE WHEN specific_date IS NOT NULL THEN specific_date ELSE '9999-99-99' END,
                    day_of_week,
                    start_time
            ''', (barber_id,))
        else:
            cursor.execute('''
                SELECT id, day_of_week, specific_date, start_time, end_time, is_available
                FROM barber_availability
                WHERE barber_id = ? AND is_active = 1
                ORDER BY 
                    CASE WHEN specific_date IS NOT NULL THEN specific_date ELSE '9999-99-99' END,
                    day_of_week,
                    start_time
            ''', (barber_id,))
        
        availability = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify({'availability': availability})
    
    elif request.method == 'POST':
        data = request.json
        availability_id = str(uuid.uuid4())
        day_of_week = data.get('dayOfWeek')
        specific_date = data.get('specificDate')
        start_time = data.get('startTime')
        end_time = data.get('endTime')
        is_available = 1 if data.get('isAvailable', True) else 0
        
        if IS_PRODUCTION:
            cursor.execute('''
                INSERT INTO barber_availability 
                (id, barber_id, day_of_week, specific_date, start_time, end_time, is_available, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 1)
            ''', (availability_id, barber_id, day_of_week, specific_date, start_time, end_time, is_available))
        else:
            cursor.execute('''
                INSERT INTO barber_availability 
                (id, barber_id, day_of_week, specific_date, start_time, end_time, is_available, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            ''', (availability_id, barber_id, day_of_week, specific_date, start_time, end_time, is_available))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'id': availability_id}), 201

@app.route('/api/barber/availability/<availability_id>', methods=['DELETE'])
def delete_availability(availability_id):
    """Delete barber availability"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if IS_PRODUCTION:
        cursor.execute('DELETE FROM barber_availability WHERE id = %s', (availability_id,))
    else:
        cursor.execute('DELETE FROM barber_availability WHERE id = ?', (availability_id,))
    
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/barber/<barber_id>/reservations', methods=['GET'])
def barber_reservations(barber_id):
    """Get barber's reservations"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if IS_PRODUCTION:
        cursor.execute('''
            SELECT r.*, s.name as service_name, s.duration_minutes
            FROM reservations r
            INNER JOIN services s ON r.service_id = s.id
            WHERE r.barber_id = %s
            ORDER BY r.start_time DESC
        ''', (barber_id,))
    else:
        cursor.execute('''
            SELECT r.*, s.name as service_name, s.duration_minutes
            FROM reservations r
            INNER JOIN services s ON r.service_id = s.id
            WHERE r.barber_id = ?
            ORDER BY r.start_time DESC
        ''', (barber_id,))
    
    reservations = []
    for row in cursor.fetchall():
        reservation = dict(row)
        # Format datetime fields to remove timezone info
        if 'start_time' in reservation and reservation['start_time']:
            if isinstance(reservation['start_time'], str):
                # Already a string, remove timezone
                reservation['start_time'] = reservation['start_time'].replace('+00:00', '').replace('Z', '')
            else:
                # It's a datetime object, format without timezone
                reservation['start_time'] = reservation['start_time'].strftime('%Y-%m-%dT%H:%M:%S')
        
        if 'end_time' in reservation and reservation['end_time']:
            if isinstance(reservation['end_time'], str):
                reservation['end_time'] = reservation['end_time'].replace('+00:00', '').replace('Z', '')
            else:
                reservation['end_time'] = reservation['end_time'].strftime('%Y-%m-%dT%H:%M:%S')
        
        reservations.append(reservation)
    
    conn.close()
    return jsonify({'reservations': reservations})

@app.route('/api/reservations', methods=['POST'])
def create_reservation():
    """Create a new reservation"""
    try:
        data = request.json
        reservation_id = str(uuid.uuid4())
        
        customer_name = data.get('customerName')
        service_id = data.get('serviceId')
        barber_id = data.get('barberId')
        start_time = data.get('startTime')
        
        if not all([customer_name, service_id, barber_id, start_time]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get service details
        if IS_PRODUCTION:
            cursor.execute('SELECT name, duration_minutes FROM services WHERE id = %s', (service_id,))
        else:
            cursor.execute('SELECT name, duration_minutes FROM services WHERE id = ?', (service_id,))
        
        service = cursor.fetchone()
        if not service:
            conn.close()
            return jsonify({'error': 'Service not found'}), 404
            
        service_name = service['name']
        duration = service['duration_minutes']
        
        # Get barber name
        if IS_PRODUCTION:
            cursor.execute('SELECT name FROM barbers WHERE id = %s', (barber_id,))
        else:
            cursor.execute('SELECT name FROM barbers WHERE id = ?', (barber_id,))
        
        barber = cursor.fetchone()
        if not barber:
            conn.close()
            return jsonify({'error': 'Barber not found'}), 404
            
        barber_name = barber['name']
        
        # Parse datetime (treat as local time, not UTC)
        start_dt = datetime.fromisoformat(start_time.replace('Z', ''))
        end_dt = start_dt + timedelta(minutes=duration)
        
        if IS_PRODUCTION:
            cursor.execute('''
                INSERT INTO reservations 
                (id, customer_name, service_id, barber_id, start_time, end_time, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'PENDING')
            ''', (reservation_id, customer_name, service_id, barber_id, start_dt, end_dt))
        else:
            cursor.execute('''
                INSERT INTO reservations 
                (id, customer_name, service_id, barber_id, start_time, end_time, status)
                VALUES (?, ?, ?, ?, ?, ?, 'PENDING')
            ''', (reservation_id, customer_name, service_id, barber_id, start_dt.isoformat(), end_dt.isoformat()))
        
        conn.commit()
        conn.close()
        
        # Return reservation object expected by frontend
        return jsonify({
            'success': True,
            'reservation': {
                'id': reservation_id,
                'customer_name': customer_name,
                'service_name': service_name,
                'barber_name': barber_name,
                'start_time': start_dt.isoformat(),
                'end_time': end_dt.isoformat(),
                'status': 'PENDING'
            }
        }), 201
    except Exception as e:
        print(f"Error creating reservation: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/reservations/<reservation_id>/status', methods=['PATCH'])
def update_reservation_status(reservation_id):
    """Update reservation status"""
    data = request.json
    status = data.get('status')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if IS_PRODUCTION:
        cursor.execute('UPDATE reservations SET status = %s WHERE id = %s', (status, reservation_id))
    else:
        cursor.execute('UPDATE reservations SET status = ? WHERE id = ?', (status, reservation_id))
    
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/available-barbers', methods=['GET'])
def get_available_barbers():
    """Get available barbers for a service and time"""
    service_id = request.args.get('serviceId')
    date_time_str = request.args.get('dateTime')
    
    if not service_id or not date_time_str:
        return jsonify({'error': 'Missing parameters'}), 400
    
    requested_datetime = datetime.fromisoformat(date_time_str.replace('Z', '+00:00'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get service duration
    if IS_PRODUCTION:
        cursor.execute('SELECT duration_minutes FROM services WHERE id = %s', (service_id,))
    else:
        cursor.execute('SELECT duration_minutes FROM services WHERE id = ?', (service_id,))
    
    service = cursor.fetchone()
    if not service:
        conn.close()
        return jsonify({'error': 'Service not found'}), 404
    
    duration_minutes = service['duration_minutes']
    end_datetime = requested_datetime + timedelta(minutes=duration_minutes)
    
    day_of_week = (requested_datetime.weekday() + 1) % 7
    requested_start_time = requested_datetime.strftime('%H:%M')
    requested_end_time = end_datetime.strftime('%H:%M')
    requested_date = requested_datetime.strftime('%Y-%m-%d')
    
    # Find available barbers
    if IS_PRODUCTION:
        cursor.execute('''
            SELECT DISTINCT b.id, b.name, b.bio
            FROM barbers b
            INNER JOIN barber_availability ba ON b.id = ba.barber_id
            INNER JOIN barber_services bs ON b.id = bs.barber_id
            WHERE b.is_active = 1
            AND ba.is_active = 1
            AND ba.is_available = 1
            AND bs.service_id = %s
            AND (
                (ba.specific_date = %s AND ba.start_time <= %s AND ba.end_time >= %s)
                OR (ba.specific_date IS NULL AND ba.day_of_week = %s AND ba.start_time <= %s AND ba.end_time >= %s)
            )
            ORDER BY b.name
        ''', (service_id, requested_date, requested_start_time, requested_end_time,
              day_of_week, requested_start_time, requested_end_time))
    else:
        cursor.execute('''
            SELECT DISTINCT b.id, b.name, b.bio
            FROM barbers b
            INNER JOIN barber_availability ba ON b.id = ba.barber_id
            INNER JOIN barber_services bs ON b.id = bs.barber_id
            WHERE b.is_active = 1
            AND ba.is_active = 1
            AND ba.is_available = 1
            AND bs.service_id = ?
            AND (
                (ba.specific_date = ? AND ba.start_time <= ? AND ba.end_time >= ?)
                OR (ba.specific_date IS NULL AND ba.day_of_week = ? AND ba.start_time <= ? AND ba.end_time >= ?)
            )
            ORDER BY b.name
        ''', (service_id, requested_date, requested_start_time, requested_end_time,
              day_of_week, requested_start_time, requested_end_time))
    
    barbers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({'barbers': barbers})

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'database': 'PostgreSQL' if IS_PRODUCTION else 'SQLite'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=not IS_PRODUCTION)

