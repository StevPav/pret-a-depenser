import pickle
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import shap
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from sklearn import model_selection
from sklearn.neighbors import NearestNeighbors
import seaborn as sns
import dvc.api
import lightgbm

st.set_page_config(layout="wide")


def load_data():
	'''Fonction chargeant et calculant les données nécessaires au dashboard.
	Ne prend pas de paramètres en entrée
	'''

	# Chargement du modèle pré-entrainé	
	pickle_in = dvc.api.read('lgbm_model.pkl',
    repo='https://github.com/StevPav/Streamlit-to-Heroku.git',
    mode='rb')
	#pickle_in=open('lgbm_model.pkl', 'rb')
	lgbm=pickle.loads(pickle_in)

	#Chargement des données de test
	db_test=pd.read_csv('https://github.com/StevPav/Streamlit-to-Heroku/blob/7d55ef87619bd98f55195541061e84c9de012e6e/df_app.csv?raw=true')
	db_test['YEARS_BIRTH']=(db_test['DAYS_BIRTH']/-365).apply(lambda x: int(x))
	db_test=db_test.reset_index(drop=True)
	df_test=pd.read_csv('https://github.com/StevPav/Streamlit-to-Heroku/blob/7d55ef87619bd98f55195541061e84c9de012e6e/df_test.csv?raw=true')

	#Calcul des SHAP values
	explainer = shap.TreeExplainer(lgbm)
	shap_values = explainer.shap_values(df_test)[1]
	exp_value=explainer.expected_value[1]
	return db_test,df_test,shap_values,lgbm,exp_value


def tab_client(db_test):

	'''Fonction pour afficher le tableau du portefeuille client avec un système de 6 champs de filtres
	permettant une recherche plus précise.
	Le paramètre est le dataframe des clients
	'''
	st.title('Dashboard Pret à dépenser')
	st.subheader('Tableau clientèle')
	row0_1,row0_spacer2,row0_2,row0_spacer3,row0_3,row0_spacer4,row_spacer5 = st.columns([1,.1,1,.1,1,.1,4])

	#Définition des filtres via selectbox
	sex=row0_1.selectbox("Sexe",['All']+db_test['CODE_GENDER'].unique().tolist())
	age=row0_1.selectbox("Age",['All']+(np.sort(db_test['YEARS_BIRTH'].unique()).astype(str).tolist()))
	fam=row0_2.selectbox("Statut familial",['All']+db_test['NAME_FAMILY_STATUS'].unique().tolist())
	child=row0_2.selectbox("Enfants",['All']+(np.sort(db_test['CNT_CHILDREN'].unique()).astype(str).tolist()))
	pro=row0_3.selectbox("Statut pro.",['All']+db_test['NAME_INCOME_TYPE'].unique().tolist())
	stud=row0_3.selectbox("Niveau d'études",['All']+db_test['NAME_EDUCATION_TYPE'].unique().tolist())

	#Affichage du dataframe selon les filtres définis
	db_display=db_test[['SK_ID_CURR','CODE_GENDER','YEARS_BIRTH','NAME_FAMILY_STATUS','CNT_CHILDREN',
	'NAME_EDUCATION_TYPE','FLAG_OWN_CAR','FLAG_OWN_REALTY','NAME_HOUSING_TYPE',
	'NAME_INCOME_TYPE','AMT_INCOME_TOTAL','AMT_CREDIT','AMT_ANNUITY']]
	db_display['YEARS_BIRTH']=db_display['YEARS_BIRTH'].astype(str)
	db_display['CNT_CHILDREN']=db_display['CNT_CHILDREN'].astype(str)
	db_display['AMT_INCOME_TOTAL']=db_test['AMT_INCOME_TOTAL'].apply(lambda x: int(x))
	db_display['AMT_CREDIT']=db_test['AMT_CREDIT'].apply(lambda x: int(x))
	db_display['AMT_ANNUITY']=db_test['AMT_ANNUITY'].apply(lambda x: x if pd.isna(x) else int(x))

	db_display=filter(db_display,'CODE_GENDER',sex)
	db_display=filter(db_display,'YEARS_BIRTH',age)
	db_display=filter(db_display,'NAME_FAMILY_STATUS',fam)
	db_display=filter(db_display,'CNT_CHILDREN',child)
	db_display=filter(db_display,'NAME_INCOME_TYPE',pro)
	db_display=filter(db_display,'NAME_EDUCATION_TYPE',stud)

	st.dataframe(db_display)
	st.markdown("**Total clients correspondants: **"+str(len(db_display)))

def filter(df,col,value):
	'''Fonction pour filtrer le dataframe selon la colonne et la valeur définies'''
	if value!='All':
		db_filtered=df.loc[df[col]==value]
	else:
		db_filtered=df
	return db_filtered


def score_viz(lgbm,df_test,client,exp_value,shap_values):
	"""Fonction principale de l'onglet 'Score visualisation' """
	st.title('Dashboard Pret à dépenser')
	st.subheader('Visualisation score')

	score,result=prediction(lgbm,df_test,client)

	fig = go.Figure(go.Indicator(
	mode = "gauge+number+delta",
    value = score,
    number = {'font':{'size':48}},
    domain = {'x': [0, 1], 'y': [0, 1]},
    title = {'text': result.tolist(), 'font': {'size': 28, 'color':color(result)}},
    delta = {'reference': 0.5, 'increasing': {'color': "red"},'decreasing':{'color':'green'}},
    gauge = {
        'axis': {'range': [0,1], 'tickcolor': color(result)},
        'bar': {'color': color(result)},
        'steps': [
            {'range': [0,0.5], 'color': 'lightgreen'},
            {'range': [0.5,1], 'color': 'lightcoral'}],
        'threshold': {
            'line': {'color': "black", 'width': 5},
            'thickness': 1,
            'value': 0.5}}))


	st.plotly_chart(fig)

	st_shap(shap.force_plot(exp_value, shap_values[client], features = df_test.iloc[client], feature_names=df_test.columns, figsize=(12,5)))

def prediction(model,df_test,id):
	'''Fonction permettant de prédire la capacité du client à rembourser son emprunt.
	les paramètres sont le modèle, le dataframe et l'ID du client'''
	y_pred=model.predict_proba(df_test)[id,1]
	decision=np.where(y_pred>0.5,"Rejected","Approved")
	return y_pred,decision

def color(pred):
	'''Définition de la couleur selon la prédiction'''
	if pred=='Approved':
		col='Green'
	else :
		col='Red'
	return col

def st_shap(plot, height=None):
	"""Fonction permettant l'affichage de graphique shap values"""
	shap_html = f"<head>{shap.getjs()}</head><body>{plot.html()}</body>"
	components.html(shap_html, height=height)

def get_client(db_test):
	"""Sélection d'un client via une selectbox"""
	client=st.sidebar.selectbox('Client',db_test['SK_ID_CURR'])
	idx_client=db_test.index[db_test['SK_ID_CURR']==client][0]
	return client,idx_client

def infos_client(db_test,client,idx_client):
	"""Affichage des infos du client sélectionné dans la barre latérale"""
	st.sidebar.markdown("**ID client: **"+str(client))
	st.sidebar.markdown("**Sexe: **"+db_test.loc[idx_client,'CODE_GENDER'])
	st.sidebar.markdown("**Statut familial: **"+db_test.loc[idx_client,'NAME_FAMILY_STATUS'])
	st.sidebar.markdown("**Enfants: **"+str(db_test.loc[idx_client,'CNT_CHILDREN']))
	st.sidebar.markdown("**Age: **"+str(db_test.loc[idx_client,'YEARS_BIRTH']))	
	st.sidebar.markdown("**Statut pro.: **"+db_test.loc[idx_client,'NAME_INCOME_TYPE'])
	st.sidebar.markdown("**Niveau d'études: **"+db_test.loc[idx_client,'NAME_EDUCATION_TYPE'])


def comparaison(df_test,db_test,idx_client):
	"""Fonction principale de l'onglet 'Comparaison clientèle' """
	st.title('Dashboard Pret à dépenser')
	st.subheader('Comparaison clientèle')
	idx_neigh,total=get_neigh(df_test,idx_client)
	db_neigh=db_test.loc[idx_neigh,['SK_ID_CURR','CODE_GENDER','YEARS_BIRTH','NAME_FAMILY_STATUS','CNT_CHILDREN',
	'NAME_EDUCATION_TYPE','FLAG_OWN_CAR','FLAG_OWN_REALTY','NAME_HOUSING_TYPE',
	'NAME_INCOME_TYPE','AMT_INCOME_TOTAL','AMT_CREDIT','AMT_ANNUITY']]
	db_neigh['AMT_INCOME_TOTAL']=db_neigh['AMT_INCOME_TOTAL'].apply(lambda x: int(x))
	db_neigh['AMT_CREDIT']=db_neigh['AMT_CREDIT'].apply(lambda x: int(x))
	db_neigh['AMT_ANNUITY']=db_neigh['AMT_ANNUITY'].apply(lambda x: x if pd.isna(x) else int(x))

	if total:
		display_charts(db_test,idx_client)

	else:
		display_charts(db_neigh,idx_client)


def get_neigh(df,idx_client):
	"""Calcul des voisins les plus proches du client sélectionné
	Sélection du nombre de voisins par un slider.
	Retourne les proches voisins et un booléen indiquant la clientèle globale ou non"""
	row1,row_spacer1,row2,row_spacer2 = st.columns([1,.1,.3,3])
	size=row1.slider("Taille du groupe de comparaison",min_value=10,max_value=1000,value=500)
	row2.write('')
	total=row2.button(label="Clientèle globale")
	neigh= NearestNeighbors(n_neighbors=size)
	neigh.fit(df)
	k_neigh=neigh.kneighbors(df.loc[idx_client].values.reshape(1,-1),return_distance=False)[0]
	k_neigh=np.sort(k_neigh)
	return k_neigh,total

def display_charts(df,client):
	"""Affichae des graphes de comparaison pour le client sélectionné """
	row1_1,row1_2,row1_3 = st.columns(3)
	st.write('')
	row2_10,row2_2,row2_3 = st.columns(3)
	
	chart_kde("Répartition de l'age",row1_1,df,'YEARS_BIRTH',client)
	chart_kde("Répartition des revenus",row1_2,df,'AMT_INCOME_TOTAL',client)
	chart_bar("Répartition du nombre d'enfants",row1_3,df,'CNT_CHILDREN',client)

	chart_bar("Répartition du statut professionel",row2_10,df,'NAME_INCOME_TYPE',client)
	chart_bar("Répartition du niveau d'études",row2_2,df,'NAME_EDUCATION_TYPE',client)
	chart_bar("Répartition du type de logement",row2_3,df,'NAME_HOUSING_TYPE',client)
	st.dataframe(df[['SK_ID_CURR','CODE_GENDER','YEARS_BIRTH','NAME_FAMILY_STATUS','CNT_CHILDREN',
	'NAME_EDUCATION_TYPE','FLAG_OWN_CAR','FLAG_OWN_REALTY','NAME_HOUSING_TYPE',
	'NAME_INCOME_TYPE','AMT_INCOME_TOTAL','AMT_CREDIT','AMT_ANNUITY']])

def chart_kde(title,row,df,col,client):
	"""Définition des graphes KDE avec une barre verticale indiquant la position du client"""
	with row:
		st.subheader(title)
		fig,ax = plt.subplots()
		sns.kdeplot(df[col],color='steelblue')
		plt.axvline(x=df.loc[client,col],ymax=0.95,color='red')
		st.pyplot(fig)

def chart_bar(title,row,df,col,client):
	"""Définition des graphes barres avec une barre horizontale indiquant la position du client"""
	with row:
		st.subheader(title)
		fig,ax = plt.subplots()
		sns.countplot(y=df[col],color='steelblue')
		plt.axhline(y=df.loc[client,col],xmax=0.95,color='red')
		st.pyplot(fig)


def main():
	"""Fonction principale permettant l'affichage de la fenêtre latérale avec les 3 onglets.
	"""
	db_test,df_test,shap_values,lgbm,exp_value=load_data()

	PAGES = [
	    "Tableau clientèle",
	    "Visualisation score",
	    "Comparaison clientèle"
	]
	st.sidebar.write('')
	st.sidebar.write('')
	st.sidebar.write('')
	st.sidebar.write('')
	st.sidebar.title('Pages')
	selection = st.sidebar.radio("Go to", PAGES)

	if selection=="Tableau clientèle":
		tab_client(db_test)
	if selection=="Visualisation score":
		client,idx_client=get_client(db_test)
		infos_client(db_test,client,idx_client)
		score_viz(lgbm,df_test,idx_client,exp_value,shap_values)
	if selection=="Comparaison clientèle":
		client,idx_client=get_client(db_test)
		infos_client(db_test,client,idx_client)
		comparaison(df_test,db_test,idx_client)

if __name__ == '__main__':
	main()



