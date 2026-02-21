import pandas as pd
import plotly.express as px
import ipywidgets as widgets

import streamlit as st

st.markdown(" # Web App d'Edouard")

st.text(" Plus gros pollueur de la planète 👋 ")




# aide
# https://stcheatsheet.streamlit.app/

# TODO: Load dataset
@st.cache_data
def load_data():
    file_path="data/CO2_per_capita.csv"
    df = pd.read_csv(file_path, sep=";")
    return df

@st.cache_data
def load_continent():
    file_path="data/geo_data.csv"
    geo = pd.read_csv(file_path, sep=";")
    return geo

geo_data = load_continent()
df=load_data()

def co2_df(start_year=2008, end_year=2018, nb_country=5):
    filtered_df = df[(df['Year'] >= start_year) & (df['Year'] <= end_year)].groupby('Country Name')['CO2 Per Capita (metric tons)']\
    .mean().sort_values(ascending=False).head(nb_country).reset_index()

  
        
# 3. Bar plot Plotly
    fig = px.bar(
        filtered_df,
        x='Country Name',
        y='CO2 Per Capita (metric tons)',
        title=f"Top {nb_country} countries by average CO2 per capita ({start_year}-{end_year})"
    )
    return fig


#try the function here

range=st.radio("Pick one", [10,20,50])

num= st.number_input("Top n", 1, 10,4)
start_year = st.slider("Pick a start date", 1960, 2011, value= 2000,step=1)
end_year = start_year + range

fig = co2_df(start_year, end_year, num)
st.plotly_chart(fig)

'''

#Selects the two most important columns in a new DataFrame (in this case we want to retrieve the continent information)
continent=geo_data[['Three_Letter_Country_Code', 'Continent_Name']]
#Merge the two DataFrames on the country code
df_tot = df.merge(continent, left_on='Country Code', right_on='Three_Letter_Country_Code', how='left')


def co2_df_conti(start_year=2008, end_year=2018, nb_country=5):
    filtered_df = df_tot[(df_tot['Year'] >= start_year) & (df_tot['Year'] <= end_year)].groupby('Continent_Name_x')['CO2 Per Capita (metric tons)']\
    .mean().sort_values(ascending=False).head(nb_country).reset_index()  

fig2 = co2_df_conti(start_year, end_year, num)
st.plotly_chart(fig2)    '''