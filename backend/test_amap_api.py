#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test AMap API connectivity"""

import requests
import os

# AMap API Key (Web Service)
AMAP_WEB_KEY = "e471e7d99965ef1f1a0d4113f580f5db"

def test_geocode():
    """Test geocoding"""
    url = "https://restapi.amap.com/v3/geocode/geo"
    params = {
        "key": AMAP_WEB_KEY,
        "address": "Beijing Chaoyang",
        "output": "json"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        print(f"     Response status: {data.get('status')}")
        print(f"     Response info: {data.get('info')}")
        print(f"     Infocode: {data.get('infocode')}")
        
        if data.get("status") == "1":
            geocodes = data.get("geocodes", [])
            if geocodes:
                location = geocodes[0].get("location", "").split(",")
                print(f"[OK] Geocode API works!")
                print(f"     Address: Beijing Chaoyang")
                print(f"     Coords: lng={location[0]}, lat={location[1]}")
                return True
        print(f"[FAIL] Geocode failed: {data.get('info')}")
        return False
    except Exception as e:
        print(f"[ERROR] Request failed: {e}")
        return False

def test_driving_route():
    """Test driving route"""
    url = "https://restapi.amap.com/v3/direction/driving"
    params = {
        "key": AMAP_WEB_KEY,
        "origin": "116.481028,39.989643",
        "destination": "116.465302,40.004717",
        "extensions": "all",
        "output": "json"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get("status") == "1":
            route = data.get("route", {})
            paths = route.get("paths", [])
            if paths:
                path = paths[0]
                print(f"[OK] Driving Route API works!")
                print(f"     Distance: {int(path.get('distance', 0)) / 1000} km")
                print(f"     Duration: {int(path.get('duration', 0)) / 60} min")
                print(f"     Tolls: {path.get('tolls', 0)} yuan")
                return True
        print(f"[FAIL] Route planning failed: {data.get('info')}")
        return False
    except Exception as e:
        print(f"[ERROR] Request failed: {e}")
        return False

def test_traffic():
    """Test traffic status"""
    url = "https://restapi.amap.com/v3/traffic/status/around"
    params = {
        "key": AMAP_WEB_KEY,
        "location": "116.481028,39.989643",
        "radius": 1000,
        "extensions": "all",
        "output": "json"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get("status") == "1":
            traffic = data.get("trafficinfo", {})
            evaluation = traffic.get("evaluation", {})
            print(f"[OK] Traffic API works!")
            print(f"     Status: {evaluation.get('status')}")
            print(f"     Desc: {evaluation.get('description')}")
            return True
        print(f"[FAIL] Traffic query failed: {data.get('info')}")
        return False
    except Exception as e:
        print(f"[ERROR] Request failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("AMap API Connectivity Test")
    print("=" * 50)
    print()
    
    print("[1] Testing Geocode API...")
    test_geocode()
    print()
    
    print("[2] Testing Driving Route API...")
    test_driving_route()
    print()
    
    print("[3] Testing Traffic API...")
    test_traffic()
    print()
    
    print("=" * 50)
    print("Test Complete!")
