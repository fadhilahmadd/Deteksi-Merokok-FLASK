import streamlit as st
import pandas as pd
import mysql.connector
import matplotlib.pyplot as plt

def visualize_most_frequent_time():
    # Establish a connection to the MySQL database
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="deteksimerokok"
    )

    # Execute SQL query to retrieve the "waktu" and "kondisi" columns data
    cursor = db.cursor()
    cursor.execute('SELECT waktu, kondisi FROM data')
    data = cursor.fetchall()

    # Convert fetched data into a pandas DataFrame
    df = pd.DataFrame(data, columns=['waktu', 'kondisi'])

    # Extract year, month, day, and time ("%H:%M") from datetime
    df['year'] = df['waktu'].dt.year
    df['month'] = df['waktu'].dt.month
    df['day'] = df['waktu'].dt.day
    df['time'] = df['waktu'].dt.strftime('%H:%M')

    # Combine year, month, and day into a single column
    df['date'] = df['year'].astype(str) + '/' + df['month'].astype(str) + '/' + df['day'].astype(str)

    # Determine the most frequent condition and time by year, month, and day
    most_frequent_conditions = df.groupby(['date'])[['kondisi', 'time']].agg(lambda x: x.value_counts().idxmax())

    # Determine the most frequent year/month/day
    most_frequent_dates = df['date'].value_counts().head()

    # Create a bar plot
    fig, ax = plt.subplots()
    most_frequent_dates.plot(kind='bar', ax=ax)

    # Customize the plot
    ax.set_xlabel('Date')
    ax.set_ylabel('Count')
    ax.set_title('Most Frequent Year/Month/Day')

    # Rotate x-axis labels for better visibility
    plt.xticks(rotation=45)

    # Display the result and the bar plot
    st.title('Waktu Paling Banyak Terdeteksi Berdasarkan Hari/Bulan/Tahun')
    st.dataframe(most_frequent_conditions)

    # Display the result and the bar plot
    st.title('Bar Plot berdasarkan Tahun/Bulan/Hari yang terdeteksi')
    st.pyplot(fig)

if __name__ == '__main__':
    visualize_most_frequent_time()