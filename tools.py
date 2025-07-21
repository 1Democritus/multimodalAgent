from langchain_core.tools import tool
import matplotlib.pyplot as plt
from scipy.stats import zscore
import io
import base64

#possible additions:
#encoder for qualitative data

def plotDataWrapper(df): #I use wrappers because it allows the tools to access internal variables within agents such as dataframes
    @tool
    def plotData(xLabel: str, yLabel: str):
        """Used to plot a group of x data and y data, giving both axes an appropriate label"""
        plt.plot(df[xLabel], df[yLabel])
        plt.xlabel(xLabel)
        plt.ylabel(yLabel)
        buffer = io.BytesIO() #saves plot into buffer file
        plt.savefig(buffer, format = 'png')
        plt.close()
        buffer.seek(0) #moves internal pointer from end of data to start
        imgBase64 = base64.b64encode(buffer.read()).decode('utf-8')
        return imgBase64
    return plotData

def displayDataWrapper():
    @tool
    def displayData(bufferFile):
        """Used to display data after plotting it, or after the user wants to see it again"""
        return bufferFile
    return displayData

def displayDistributionWrapper(df): #should fix this later
    @tool
    def displayDistribution(columnName: str):
        """Used to show counts of different instances of data on a column"""
        if df[columnName].dtype != "int64" and df[columnName].dtype != "float":
            return "This data can't be visualised due to the data type being incompatible"
        fig, ax = plt.subplots()
        df.hist(columnName, ax = ax)
        buffer = io.BytesIO()
        fig.savefig(buffer, format = "png")
        buffer.seek(0)
        imgBase64 = base64.b64encode(buffer.read()).decode('utf-8')
        return imgBase64
    return displayDistribution

def checkMaxCorrelationWrapper(df):
    @tool
    def checkMaxCorrelation(column: str, x: int):
        """Used to top x highest correlations with a column"""
        columnList = []
        for idx in df.columns:
            try:
                correlation = df[column].corr(df[idx])
                if idx != column and correlation > columnList[x-1][0]:
                    columnList[x-1] = (correlation, idx)
            except IndexError: #meaning issue arises from list size, not data being qualitative
                columnList.append((correlation, idx))
            columnList = sorted(columnList, reverse = True)
        return str(columnList)
    return checkMaxCorrelation

def checkMinCorrelationWrapper(df):
    @tool
    def checkMinCorrelation(column: str, x: int):
        """Used to top x lowest correlations with a column"""
        columnList = []
        for idx in df.columns:
            try:
                correlation = df[column].corr(df[idx])
                if idx != column and correlation < columnList[x-1][0]:
                    columnList[x-1] = (correlation, idx)
            except IndexError:
                columnList.append((correlation, idx))
            columnList = sorted(columnList)
        return str(columnList)
    return checkMinCorrelation

def checkForAnomaliesWrapper(df):
    @tool
    def checkForAnomalies(columnName: str, threshold: float):
        """Used to find data that don't correspond to the general trend"""
        zscores = zscore(df[columnName])
        anomalyList = [(f"row {row}", zscores[row]) for row in range(len(df)) if abs(zscores[row]) >= threshold] #this format will make finding anomalies easier
        return str(anomalyList)
    return checkForAnomalies

def filterColumnsWrapper(df):
    @tool
    def filterColumns(threshold: float, label: str):
        """Used to remove columns which don't have a correlation with a chosen column name above a chosen threshold"""
        filteredColumns = []
        for column in df.columns:
            try:
                if df[label].corr(df[column]) < threshold: #checking for correlation
                    filteredColumns.append(column)
            except:
                filteredColumns.append(column)

        return filteredColumns
    return filterColumns

def checkNANStatsWrapper(df):
    @tool
    def checkNANStats():
        """Checks the count of empty values on the database, which is shown as NaN"""
        nanSum = df.isna().sum()
        return str(nanSum)
    return checkNANStats

def returnDescriptionWrapper(df):
    @tool
    def returnDescription(column: str):
        """Returns some important statistics about the passed column in the database"""
        description = df[column].describe()
        return str(description)
    return returnDescription