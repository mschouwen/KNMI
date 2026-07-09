import pandas as pd
import numpy as np

def rate_thermal_comfort(temp, rh):
    """
    Approximates Mieczkowski's thermal comfort rating (0 to 5) 
    using temperature (°C) and relative humidity (%).
    """
    # Simple linear heuristic representing standard effective temperature curves
    if 20 <= temp <= 26:
        return 5.0
    elif 15 <= temp < 20:
        return 4.0 + (temp - 15) / 5.0
    elif 26 < temp <= 32:
        return 5.0 - (temp - 26) / 3.0
    elif 10 <= temp < 15:
        return 2.0 + (temp - 10) / 2.5
    elif 32 < temp <= 38:
        return 3.0 - (temp - 32) / 3.0
    else:
        return 0.0

def calculate_netherlands_tci(cid, cia, r, s, w):
    """
    Calculates the Tourism Climate Index (TCI) adapted for the Netherlands.
    Formula: TCI = 2 * (4 * CID + CIA + 2 * R + 2 * S + W)
    
    Parameters (all must be rated values between 0 and 5):
        cid (float): Daytime Comfort Index 
        cia (float): Daily Comfort Index
        r   (float): Precipitation Rating
        s   (float): Sunshine Rating
        w   (float): Wind Speed Rating
        
    Returns:
        float: Final TCI score scaled perfectly from 0 to 100.
    """
    # 1. Input Guardrails
    ratings = {'CID': cid, 'CIA': cia, 'R': r, 'S': s, 'W': w}
    for name, val in ratings.items():
        if not (-30 <= val <= 5):
            raise ValueError(f"The rated value for {name} must be between 0 and 5. Got: {val}")
            
    # 2. The Netherlands/European Adapted Formula
    tci_score = 2 * (4 * cid + cia + 2 * r + 2 * s + w)
    
    return float(tci_score)

def rate_precipitation(monthly_rainfall_mm):
    """
    Example rating function for Precipitation (R).
    Based on standard TCI classification for monthly rainfall.
    """
    if monthly_rainfall_mm <= 14.9:
        return 5.0
    elif monthly_rainfall_mm <= 29.9:
        return 4.5
    elif monthly_rainfall_mm <= 44.9:
        return 4.0
    elif monthly_rainfall_mm <= 59.9:
        return 3.5
    elif monthly_rainfall_mm <= 74.9:
        return 3.0
    elif monthly_rainfall_mm <= 89.9:
        return 2.5
    elif monthly_rainfall_mm <= 104.9:
        return 2.0
    elif monthly_rainfall_mm <= 119.9:
        return 1.5
    elif monthly_rainfall_mm <= 134.9:
        return 1.0
    elif monthly_rainfall_mm <= 149.9:
        return 0.5
    else:
        return 0.0

def rate_sunshine(daily_sunshine_hours):
    """
    Example rating function for Sunshine (S).
    Based on standard TCI classification for average daily sunshine.
    """
    if daily_sunshine_hours >= 10:
        return 5.0
    elif daily_sunshine_hours >= 9:
        return 4.5
    elif daily_sunshine_hours >= 8:
        return 4.0
    elif daily_sunshine_hours >= 7:
        return 3.5
    elif daily_sunshine_hours >= 6:
        return 3.0
    elif daily_sunshine_hours >= 5:
        return 2.0
    elif daily_sunshine_hours >= 4:
        return 1.0
    elif daily_sunshine_hours >= 3:
        return 0.5
    else:
        return 0.0

def interpret_tci(tci_score):
    """Returns the descriptive category of the TCI score."""
    if tci_score >= 90: return "Ideal"
    if tci_score >= 80: return "Excellent"
    if tci_score >= 70: return "Very Good"
    if tci_score >= 60: return "Good"
    if tci_score >= 50: return "Acceptable"
    if tci_score >= 40: return "Marginal"
    if tci_score >= 30: return "Unfavorable"
    if tci_score >= 20: return "Very Unfavorable"
    if tci_score >= 10: return "Extremely Unfavorable"
    return "Impossible"

def calculate_rated_daily_comfort(t_mean, rh_mean):
    """
    Approximates the Daily Comfort Index (CIA) for the Tourist Climate Index (TCI).
    Maps Mean Temperature (°C) and Mean Relative Humidity (%) to a rating of -3 to 5.
    
    Parameters:
    t_mean (float or pd.Series): Mean daily air temperature in Celsius
    rh_mean (float or pd.Series): Mean daily relative humidity in %
    
    Returns:
    int or pd.Series: The CIA rating score (-3 to 5)
    """
    
    # 1. Calculate Effective Temperature (ET) using the Missenard formula
    # This accounts for how the humidity makes the temperature "feel" to the human body
    et = t_mean - 0.4 * (t_mean - 10) * (1 - rh_mean / 100.0)
    
    # 2. Define the rating logic based on the Effective Temperature (ET)
    def assign_rating(val):
        if 20.0 <= val <= 23.9:
            return 5    # Optimal
        elif (19.0 <= val < 20.0) or (24.0 <= val <= 24.9):
            return 4    # Excellent
        elif (18.0 <= val < 19.0) or (25.0 <= val <= 25.9):
            return 3    # Very Good
        elif (16.0 <= val < 18.0) or (26.0 <= val <= 26.9):
            return 2    # Good
        elif (14.0 <= val < 16.0) or (27.0 <= val <= 27.9):
            return 1    # Acceptable
        elif (12.0 <= val < 14.0) or (28.0 <= val <= 28.9):
            return 0    # Marginal
        elif (10.0 <= val < 12.0) or (29.0 <= val <= 29.9):
            return -1   # Unfavorable
        elif (8.0 <= val < 10.0) or (30.0 <= val <= 30.9):
            return -2   # Very Unfavorable
        else:
            return -3   # Extremely Unfavorable (val < 8.0 or val >= 31.0)

    # Handle pandas Series for bulk dataframe processing
    if isinstance(et, pd.Series):
        return et.apply(assign_rating)
    else:
        return assign_rating(et)
    
def calculate_rated_wind(wind_speed, t_max):
    """
    Calculates the Wind Rating (W) for the Tourist Climate Index (TCI).
    Accounts for different cooling regimes depending on Maximum Daily Temperature.
    
    Parameters:
    wind_speed (float or pd.Series): Mean wind speed in km/h
    t_max (float or pd.Series): Maximum daily temperature in °C to determine the regime.
    
    Returns:
    float or pd.Series: Rating score between 0.0 and 5.0
    """
    # Ensure inputs are treated consistently as numpy arrays/series for conditions
    ws = np.atleast_1d(wind_speed)
    t = np.atleast_1d(t_max)
    
    # Initialize an array for the ratings
    w_rating = np.zeros_like(ws, dtype=float)
    
    # Define condition masks based on temperature regime
    hot_climate = (t >= 24.0)
    normal_climate = ~hot_climate
    
    # ----------------------------------------------------
    # REGIME 1: Normal / Cold Climate (t_max < 24°C)
    # ----------------------------------------------------
    w_rating = np.where(normal_climate & (ws < 2.88), 5.0, w_rating)
    w_rating = np.where(normal_climate & (ws >= 2.88) & (ws < 5.76), 4.5, w_rating)
    w_rating = np.where(normal_climate & (ws >= 5.76) & (ws < 9.03), 4.0, w_rating)
    w_rating = np.where(normal_climate & (ws >= 9.03) & (ws < 12.24), 3.5, w_rating)
    w_rating = np.where(normal_climate & (ws >= 12.24) & (ws < 19.80), 3.0, w_rating)
    w_rating = np.where(normal_climate & (ws >= 19.80) & (ws < 24.30), 2.5, w_rating)
    w_rating = np.where(normal_climate & (ws >= 24.30) & (ws < 28.80), 2.0, w_rating)
    w_rating = np.where(normal_climate & (ws >= 28.80) & (ws < 38.52), 1.0, w_rating)
    w_rating = np.where(normal_climate & (ws >= 38.52), 0.0, w_rating)
    
    # ----------------------------------------------------
    # REGIME 2: Hot Climate (t_max >= 24°C) - Evaporative Cooling
    # ----------------------------------------------------
    w_rating = np.where(hot_climate & (ws < 2.88), 2.0, w_rating)
    w_rating = np.where(hot_climate & (ws >= 2.88) & (ws < 5.76), 2.5, w_rating)
    w_rating = np.where(hot_climate & (ws >= 5.76) & (ws < 9.03), 3.0, w_rating)
    w_rating = np.where(hot_climate & (ws >= 9.03) & (ws < 12.24), 4.0, w_rating)
    w_rating = np.where(hot_climate & (ws >= 12.24) & (ws < 19.80), 5.0, w_rating)
    w_rating = np.where(hot_climate & (ws >= 19.80) & (ws < 24.30), 4.0, w_rating)
    w_rating = np.where(hot_climate & (ws >= 24.30) & (ws < 28.80), 3.0, w_rating)
    w_rating = np.where(hot_climate & (ws >= 28.80) & (ws < 38.52), 1.5, w_rating)
    w_rating = np.where(hot_climate & (ws >= 38.52), 0.0, w_rating)
    
    # Return a scalar if input was scalar, else return a Series/Array
    if isinstance(wind_speed, (int, float)):
        return float(w_rating[0])
    return pd.Series(w_rating, index=wind_speed.index if isinstance(wind_speed, pd.Series) else None)    

def get_cid_rating(max_temp, min_humidity):
    """
    Calculates the CID (Daytime Comfort Index) rating (0 to 5) 
    based on Maximum Daily Temperature (Â°C) and Minimum Daily Relative Humidity (%).
    """
    # 1. Define the temperature brackets (Rows)
    # Using the standard Mieczkowski thermal comfort intervals
    temp_bins = [-np.inf, 15, 17, 19, 21, 24, 27, 29, 31, 33, np.inf]
    temp_labels = ['<15', '15-17', '17-19', '19-21', '21-24', '27', '29', '31', '33', '>33']
    
    # 2. Define the Relative Humidity brackets (Columns)
    humidity_bins = [-np.inf, 30, 40, 50, 60, 70, 80, 90, np.inf]
    humidity_labels = ['<30', '30-40', '40-50', '50-60', '60-70', '70-80', '80-90', '>90']
    
    # 3. Create the standard TCI Matrix (Rows = Temp, Columns = Humidity)
    # Ratings range from 0.0 to 5.0 based on climatic comfort.
    matrix_data = [
        # <15Â°C (Generally cold, lower scores)
        [1.0, 1.5, 2.0, 2.5, 3.0, 2.5, 2.0, 1.5], 
        # 15-17Â°C
        [2.0, 2.5, 3.0, 3.5, 4.0, 3.5, 3.0, 2.5], 
        # 17-19Â°C
        [3.0, 3.5, 4.0, 4.5, 4.5, 4.0, 3.5, 3.0], 
        # 19-21Â°C
        [4.0, 4.5, 4.5, 5.0, 4.5, 4.5, 4.0, 3.5], 
        # 21-24Â°C (The "Sweet Spot" for comfort)
        [4.5, 5.0, 5.0, 5.0, 4.5, 4.0, 3.5, 3.0], 
        # 24-27Â°C (Getting warmer)
        [4.0, 4.5, 4.5, 4.0, 3.5, 3.0, 2.5, 2.0], 
        # 27-29Â°C
        [3.5, 4.0, 3.5, 3.0, 2.5, 2.0, 1.5, 1.0], 
        # 29-31Â°C (Hot and sticky if humidity is high)
        [2.5, 3.0, 2.5, 2.0, 1.5, 1.0, 0.5, 0.0], 
        # 31-33Â°C
        [1.5, 2.0, 1.5, 1.0, 0.5, 0.0, 0.0, 0.0], 
        # >33Â°C (Extreme heat)
        [0.5, 1.0, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0]  
    ]
    
    # Build the lookup DataFrame
    df_matrix = pd.DataFrame(matrix_data, index=temp_labels, columns=humidity_labels)
    
    # 4. Find which bracket our input values fall into
    temp_category = pd.cut([max_temp], bins=temp_bins, labels=temp_labels)[0]
    humidity_category = pd.cut([min_humidity], bins=humidity_bins, labels=humidity_labels)[0]
    
    # 5. Extract the rating from the matrix
    cid_rating = df_matrix.loc[temp_category, humidity_category]
    
    return float(cid_rating) 

def calculate_tci_from_weather_data(t_max, t_mean, rh_mean, avg_humidity, monthly_rain, daily_sun, wind_speed):
    # Calculates the final TCI score for the Netherlands based on weather data.

    # 2. Convert raw data to 0-5 ratings using helper functions
    rated_R = rate_precipitation(monthly_rain)
    rated_S = rate_sunshine(daily_sun)

    # Note: CID, CIA, and Wind require complex psychrometric charts or tables 
    # based on Effective Temperature. For this example, we will assign them 
    # manually based on pre-calculated ratings.
    rated_CID = get_cid_rating(t_max, avg_humidity)  # Example values
    rated_CIA = calculate_rated_daily_comfort(t_mean, rh_mean)  # Rated Daily Comfort
    rated_W = calculate_rated_wind(wind_speed, t_max)

    # 3. Calculate final TCI
    final_tci = calculate_netherlands_tci(cid=rated_CID, cia=rated_CIA, r=rated_R, s=rated_S, w=rated_W)

    return final_tci