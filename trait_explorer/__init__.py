from fastapi import Response
import pandas as pd
from tempfile import NamedTemporaryFile


#--------- support routines for processing TERRA-Ref season measurements ----------------

def addPlotMarker(plotlist,cultivar,rng,column,selectedFeatureName,featureValue):
    mark = {}
    mark['cultivar'] = cultivar
    mark['range'] = rng
    mark['column'] = column
    mark[selectedFeatureName] = featureValue
    plotlist.append(mark)



# this method takes an input day of the season and generates an output dataframe with the most recent
# measurement of a selectedFeature taken for each location in the field.  It is a way to watch the field develop
# over time during the season.

def renderCanopyHeightOnDay(dataFrm, maxRange, maxColumn, selectedDay, selectedFeature):

    # accumulate matching measturements here
    plotlist = []

    # first get rid of observations after the query day
    before_df = dataFrm.loc[dataFrm['day_offset'] <= selectedDay]
    #print(before_df.shape)

    # group all the measurements so far by cultivar
    grouped = before_df.groupby(['range','column'])

    # now loop through these by cultivar and select only the measurement with the highest day_offset value (the most recent)
    recentlist = []
    for name, group in grouped:
        #print(name)
        selected = group['day_offset'].idxmax()  # this selects the highest value index
        # the index is a lookup into the original dataframe, so put this entry in the list for plotting
        recentlist.append(dataFrm.iloc[selected])

    # how many cultivars did we find that had a measurement on or before our day?
    #print(len(recentlist),"cultivars have been measured on or before day",selectedDay)
    recent_df = pd.DataFrame(recentlist)

    # now fill out the entire field by querying the values at each location from the
    # recent dataframe and filling in a plotting list.  This parameter list (plotlist) needs to be empty
    # before running this algorithm.

    cultivarCount = 0
    measurementCount = 0
    # go once across the entire field by using range and column indices
    for rng in range(2,int(maxRange)):
        for col in range(2,int(maxColumn)):
            #print(rng,col)
            # find which cultivar is in this spot in the field
            CultivarListInThisSpot = dataFrm.loc[(dataFrm['range'] == rng) & (dataFrm['column']==col)]['cultivar']
            print
            # return a Series of the cultivar names. If the square isn't empty, get the cultivar name from the list.
            # all cultivar names should be identical since we have selected multiple measurements (on different days) from the same location
            if len(CultivarListInThisSpot)> 0:
                cultivarCount += 1
                thisCultivar = CultivarListInThisSpot.values[0]
                thisMeasurement = recent_df.loc[(recent_df['range'] == rng) & (recent_df['column'] == col)][selectedFeature]
                # depending on the day, we might or might not have had a previous measurement, so check there was a measurement
                # before plotting.  This filter prevents a run-time error trying to plot non-existent measurements.  See the
                # "else" case below for when there is no previous measurement.
                if len(thisMeasurement)>0:
                    measurementCount += 1
                    thisMeasurementValue = thisMeasurement.values[0]
                    addPlotMarker(plotlist,thisCultivar,rng,col,selectedFeature,thisMeasurementValue)
                else:
                    # fill in empty entries for locations where there were no measurements. This happens more during
                    # the early part of the season because measurements haven't been taken in some locations yet. This
                    # way, the plot will always render the full field because all locations will have an entry, even
                    # if it is zero because no measurements have been taken yet.
                    addPlotMarker(plotlist,thisCultivar,rng,col,selectedFeature,0.0)

    plotdf = pd.DataFrame(plotlist)
    # print('cultivars found:',cultivarCount)
    # print('measurements found:',measurementCount)
    # print('plotted',len(plotlist),'values')
    return plotdf


def init(app):

    @app.get('/api/terra_trait_daily/')
    def terra_trait_daily(
        selectedDay: int = 12,
        selectedTrait: str = 'canopy_height',
    ):
        # this is a mini version of the data file that is quick to read and write here
        data_filename = 'trait_explorer/s4_height_and_models.csv'
        traits_df = pd.read_csv(data_filename)

        # find the field boundaries of the data dynamically.  It would be faster to hardcode this
        maxColumn = traits_df.describe().loc['max','column']
        maxRange = traits_df.describe().loc['max','range']

        # run the extraction of the trait values across the field at or as soon before the reqested day as possible
        plotdf = renderCanopyHeightOnDay(traits_df, maxRange, maxColumn, selectedDay, selectedTrait)
        csvContent = plotdf.to_csv(index=False)

        return Response(content=csvContent, media_type='text/csv')


    @app.get('/trait_explorer')
    def index():
        with open('trait_explorer/index.html') as indexFile:
            indexContent = indexFile.read()
        
        return Response(content=indexContent, media_type='text/html')
