"""
SIP Event Model
Database schema for Soroptimist International of Poway calendar events.
"""
from __init__ import db
from datetime import datetime


class SipEvent(db.Model):
    __tablename__ = 'sip_events'

    id = db.Column(db.Integer, primary_key=True)
    _title = db.Column(db.String(200), nullable=False)
    _date = db.Column(db.Date, nullable=False)
    _start_time = db.Column(db.String(20), nullable=False)
    _end_time = db.Column(db.String(20), nullable=False)
    _location = db.Column(db.String(300), nullable=False)
    _notes = db.Column(db.Text, nullable=True)
    _event_type = db.Column(db.String(20), default='blue')  # 'blue' | 'gold'
    _created_at = db.Column(db.DateTime, default=datetime.utcnow)
    _updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, title, date, start_time, end_time, location, notes=None, event_type='blue'):
        self._title = title
        # Accept either a date object or 'YYYY-MM-DD' string
        if isinstance(date, str):
            self._date = datetime.strptime(date, '%Y-%m-%d').date()
        else:
            self._date = date
        self._start_time = start_time
        self._end_time = end_time
        self._location = location
        self._notes = notes
        self._event_type = event_type

    def create(self):
        try:
            db.session.add(self)
            db.session.commit()
            return self
        except Exception as e:
            db.session.rollback()
            raise e

    def read(self):
        return {
            'id': self.id,
            'title': self._title,
            'date': self._date.isoformat() if self._date else None,
            'startTime': self._start_time,
            'endTime': self._end_time,
            'location': self._location,
            'notes': self._notes or '',
            'eventType': self._event_type,
            'createdAt': self._created_at.isoformat() if self._created_at else None,
            'updatedAt': self._updated_at.isoformat() if self._updated_at else None,
        }

    def update(self, data):
        try:
            if 'title' in data:
                self._title = data['title']
            if 'date' in data:
                d = data['date']
                self._date = datetime.strptime(d, '%Y-%m-%d').date() if isinstance(d, str) else d
            if 'startTime' in data:
                self._start_time = data['startTime']
            if 'endTime' in data:
                self._end_time = data['endTime']
            if 'location' in data:
                self._location = data['location']
            if 'notes' in data:
                self._notes = data['notes']
            if 'eventType' in data:
                self._event_type = data['eventType']
            self._updated_at = datetime.utcnow()
            db.session.commit()
            return self
        except Exception as e:
            db.session.rollback()
            raise e

    def delete(self):
        try:
            db.session.delete(self)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def get_all():
        events = SipEvent.query.order_by(SipEvent._date.asc()).all()
        return [e.read() for e in events]

    @staticmethod
    def get_by_id(event_id):
        return SipEvent.query.get(event_id)


def initSipEvents():
    """Seed the sip_events table with default meetings."""
    from __init__ import app, db
    with app.app_context():
        db.create_all()  # creates sip_events if it doesn't exist yet
        if SipEvent.query.first():
            print("SIP events already initialized.")
            return

        from datetime import date
        today = date.today()

        # Helper to safely set a day (clamps to last day of month)
        def safe_date(year, month, day):
            import calendar
            last = calendar.monthrange(year, month)[1]
            return date(year, month, min(day, last))

        y, m = today.year, today.month
        nm = m + 1 if m < 12 else 1
        ny = y if m < 12 else y + 1

        sample = [
            SipEvent(
                title='General Member Meeting',
                date=safe_date(y, m, 18),
                start_time='6:30 PM',
                end_time='8:00 PM',
                location='Poway Community Park, Room B',
                notes='Open to all members. Agenda and updates on current programs.',
                event_type='blue'
            ),
            SipEvent(
                title='Board Meeting',
                date=safe_date(y, m, 7),
                start_time='5:30 PM',
                end_time='7:00 PM',
                location='Poway City Hall, Conference Room 1',
                notes='Board members only. Review of financials and strategic planning.',
                event_type='gold'
            ),
            SipEvent(
                title='Celebration of Courage Planning',
                date=safe_date(y, m, 25),
                start_time='6:00 PM',
                end_time='7:30 PM',
                location='Poway Community Park, Room A',
                notes='Planning committee meeting for the annual Celebration of Courage event.',
                event_type='blue'
            ),
            SipEvent(
                title='General Member Meeting',
                date=safe_date(ny, nm, 15),
                start_time='6:30 PM',
                end_time='8:00 PM',
                location='Poway Community Park, Room B',
                notes='Open to all members. Agenda and updates on current programs.',
                event_type='blue'
            ),
            SipEvent(
                title='Board Meeting',
                date=safe_date(ny, nm, 4),
                start_time='5:30 PM',
                end_time='7:00 PM',
                location='Poway City Hall, Conference Room 1',
                notes='Board members only. Review of financials and strategic planning.',
                event_type='gold'
            ),
        ]

        for event in sample:
            db.session.add(event)
        db.session.commit()
        print(f"Initialized {len(sample)} SIP calendar events.")
