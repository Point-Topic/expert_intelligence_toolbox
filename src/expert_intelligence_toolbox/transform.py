import pandas as pd
import numpy as np

def logistic_forecast_distributed_country_growth(input_df, country_totals_df, metric: str, year_to_forecast: int, country_code: str, cap: float=1):
        print(f'Now forecasting metric {metric} in {country_code} for year {year_to_forecast}')

        metric_percent = metric + '_percent'
        metric_pop = metric + '_pop'

        country_total_input_year = country_totals_df.loc[(country_totals_df['reported_at'] == year_to_forecast-1) & (country_totals_df['country_code'] == f'{country_code}')][f'{metric_percent}'].values[0]
        country_total_forecasted_year = country_totals_df.loc[(country_totals_df['reported_at'] == year_to_forecast) & (country_totals_df['country_code'] == f'{country_code}')][f'{metric_percent}'].values[0]
        country_total_change = float(country_total_forecasted_year - country_total_input_year)
        
        regions = input_df.loc[(input_df['reported_at'] == year_to_forecast-1) & (input_df['country_code'] == f'{country_code}')][f'{metric_percent}'].values.tolist()
        ekg_ids = input_df.loc[(input_df['reported_at'] == year_to_forecast-1) & (input_df['country_code'] == f'{country_code}')]['ekg_id'].values.tolist()
        I = len(regions)
        
        shift = 0.1
        s= 0
        if country_total_change > 0:
            for i in regions:
                s += (1-i)*(i+shift)

        if country_total_change < 0:
            for i in regions:
                s += (1+shift-i)*i

        try:
            proportionality_const = country_total_change / s
        except:
            print(f'Warning: proportionality constant could not be calculated. S is: {s}, country total change is: {country_total_change}. If there is no change in country total, or regions are already at 100% or 0%, this may not be an issue.')

        if country_total_change > 0:
            try:
                regions_year2 = [i + proportionality_const*(1-i)*(i+shift)*I for i in regions]
                difference = [0]*len(regions)
                for i in range(0, len(regions)):
                    difference[i] = regions_year2[i] - regions[i]
                    
                print(f'Country total in input year {year_to_forecast-1} is {country_total_input_year}\n Country total in forecasted year {year_to_forecast} is {country_total_forecasted_year}\n Country total change (y2-y1) is {country_total_change}\n Sum of regional change is {sum(difference)/I}')
                
            except ZeroDivisionError: # if all regions have 100% or 0% coverage
                regions_year2 = regions
                print(f'Overall growth is zero. Coverage in {year_to_forecast} is equal to {year_to_forecast-1}.')
        elif country_total_change < 0:
                try:
                    regions_year2 = [i + proportionality_const*(1-i+shift)*(i)*I for i in regions]
                    difference = [0]*len(regions)
                    for i in range(0, len(regions)):
                        difference[i] = regions_year2[i] - regions[i]
                    print(f'Country total in input year {year_to_forecast-1} is {country_total_input_year}\n Country total in forecasted year {year_to_forecast} is {country_total_forecasted_year}\n Country total change (y2-y1) is {country_total_change}\n Sum of regional change is {sum(difference)/I}')
                except ZeroDivisionError: # if all regions have 100% or 0% coverage
                    regions_year2 = regions
                    print(f'Overall growth is zero. Coverage in {year_to_forecast} is equal to {year_to_forecast-1}.')
        elif country_total_change == 0:
                regions_year2 = regions
                print(f'Overall growth is zero. Coverage in {year_to_forecast} is equal to {year_to_forecast-1}.')

        output = {'ekg_id': ekg_ids, 'country_code': f'{country_code}', f'{metric_percent}': regions_year2, 'reported_at': year_to_forecast}
        output_df = pd.DataFrame(output)
        output_df[f'{metric_percent}'] = output_df[f'{metric_percent}'].apply(lambda x: round(x,4))

        return output_df

def logistic_restatement_distributed_country_growth(input_df, country_totals_df, restated_country_totals_df, metric: str, year_to_restate: int, country_code: str, cap: float=1):
        metric_percent = metric + '_percent'
        metric_pop = metric + '_pop'
        print(f'Now restating metric {metric} in {country_code} for year {year_to_restate}')

        country_total_original = country_totals_df.loc[(country_totals_df['reported_at'] == year_to_restate) & (country_totals_df['country_code'] == f'{country_code}')][f'{metric_percent}'].values[0]
        country_total_restated = restated_country_totals_df.loc[(restated_country_totals_df['reported_at'] == year_to_restate) & (restated_country_totals_df['country_code'] == f'{country_code}')][f'{metric_percent}'].values[0]
        country_total_change = float(country_total_restated - country_total_original)
        
        regions = input_df.loc[(input_df['reported_at'] == year_to_restate) & (input_df['country_code'] == f'{country_code}')][f'{metric_percent}'].values.tolist()
        ekg_ids = input_df.loc[(input_df['reported_at'] == year_to_restate) & (input_df['country_code'] == f'{country_code}')]['ekg_id'].values.tolist()
        I = len(regions)

        shift = 0.1
        s= 0
        if country_total_change > 0:
            for i in regions:
                s += (1-i)*(i+shift)

        if country_total_change < 0:
            for i in regions:
                s += (1+shift-i)*i

        try:
            proportionality_const = country_total_change / s
        except:
            print(f'Warning: proportionality constant could not be calculated. S is: {s}, country total change is: {country_total_change}. If there is no change in country total, or regions are already at 100% or 0%, this may not be an issue.')

        if country_total_change > 0 and country_total_restated is not None:
            try:
                regions_restated = [i + proportionality_const*(1-i)*(i+shift)*I for i in regions]
                difference = [0]*len(regions)
                for i in range(0, len(regions)):
                    difference[i] = regions_restated[i] - regions[i]
                print(f'Original country total in {year_to_restate} is {country_total_original}\n Restated country total is {country_total_restated}\n Country total restatement is {country_total_change}\n Sum of regional difference is {sum(difference)/I}')
            except ZeroDivisionError: # if all regions have 100% or 0% coverage
                regions_restated = regions
                print(f'Restatement is zero. Restated country total in {year_to_restate} is equal to original country total.')

        elif country_total_change < 0 and country_total_restated is not None:
                try:
                    regions_restated = [i + proportionality_const*(1-i+shift)*(i)*I for i in regions]
                    difference = [0]*len(regions)
                    for i in range(0, len(regions)):
                        difference[i] = regions_restated[i] - regions[i]
                    print(f'Original country total in {year_to_restate} is {country_total_original}\n Restated country total is {country_total_restated}\n Country total restatement is {country_total_change}\n Sum of regional difference is {sum(difference)/I}')
                except ZeroDivisionError: # if all regions have 100% or 0% coverage
                    regions_restated = regions
                    print(f'Restatement is zero. Restated country total in {year_to_restate} is equal to original country total.')
        elif country_total_change == 0 or np.isnan(country_total_restated):
                regions_restated = regions
                print(f'Overall growth is zero. Restated country total in {year_to_restate} is equal to original country total.')

        output = {'ekg_id': ekg_ids, 'country_code': f'{country_code}', f'{metric_percent}': regions_restated, 'reported_at': year_to_restate}
        output_df = pd.DataFrame(output)
        output_df[f'{metric_percent}'] = output_df[f'{metric_percent}'].apply(lambda x: round(x,4))

        return output_df