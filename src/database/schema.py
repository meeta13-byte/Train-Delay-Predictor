"""SQLAlchemy models for the railway delay analytics database."""

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Station(Base):
    __tablename__ = "stations"

    station_code = Column(String, primary_key=True)
    station_name = Column(String)
    state = Column(String)
    zone = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)


class Train(Base):
    __tablename__ = "trains"

    train_no = Column(Integer, primary_key=True)
    train_name = Column(String)
    train_type = Column(String)
    source_station_code = Column(String, foreign_key=ForeignKey("stations.station_code"))
    destination_station_code = Column(String, foreign_key=ForeignKey("stations.station_code"))
    zone = Column(String)
    distance_km = Column(Float)


class TrainStop(Base):
    __tablename__ = "train_stops"

    train_no = Column(Integer, primary_key=True, foreign_key=ForeignKey("trains.train_no"))
    stop_sequence = Column(Integer, primary_key=True)
    station_code = Column(String, foreign_key=ForeignKey("stations.station_code"))
    scheduled_arrival = Column(DateTime)
    scheduled_departure = Column(DateTime)
    distance_from_source_km = Column(Float)


class DelayRecord(Base):
    __tablename__ = "delay_records"

    record_id = Column(Integer, primary_key=True)
    date = Column(DateTime)
    train_no = Column(Integer, foreign_key=ForeignKey("trains.train_no"))
    station_code = Column(String, foreign_key=ForeignKey("stations.station_code"))
    scheduled_arrival = Column(DateTime)
    actual_arrival = Column(DateTime)
    delay_minutes = Column(Float)
    weather_condition = Column(String)
    cancelled = Column(Boolean)


class DelayRemark(Base):
    __tablename__ = "delay_remarks"

    remark_id = Column(Integer, primary_key=True)
    date = Column(String)
    train_no = Column(Integer, foreign_key=ForeignKey("trains.train_no"))
    station_code = Column(String, foreign_key=ForeignKey("stations.station_code"), nullable=True)
    delay_minutes = Column(Float)
    reason = Column(String)
