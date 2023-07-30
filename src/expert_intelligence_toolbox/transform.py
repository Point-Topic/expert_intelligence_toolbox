import pandas as pd


def logistic_forecast_distributed_country_growth(input_df, country_totals_df, metric: str, year_to_forecast: int, country_code: str, cap: float=1):
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
                s += (1-i)*(i+shift*(1-i*I))
                #print('s is',s)

        if country_total_change < 0:
            for i in regions:
                s += (1-i+shift*(i*I))*(i)
                #print('s is',s)

        if country_total_change > 0:
            try:
                proportionality_const = country_total_change / s
                regions_year2 = [i + proportionality_const*(1-i)*(i+shift*(1-i*I))* I for i in regions]
                difference = [0]*len(regions)
                for i in range(0, len(regions)):
                    difference[i] = regions_year2[i] - regions[i]
                    
                print(f'Country total in input year {year_to_forecast-1} is {country_total_input_year}\n Country total in forecasted year {year_to_forecast} is {country_total_forecasted_year}\n Country total change is {country_total_change}\n Overall growth is {sum(difference)/I}')
                
            except ZeroDivisionError: # if all regions have 100% or 0% coverage
                regions_year2 = regions
                print(f'Overall growth is zero. Coverage in {year_to_forecast} is equal to {year_to_forecast-1}.')
        elif country_total_change < 0:
                try:
                    proportionality_const = -1 * (country_total_change / s)
                    regions_year2 = [i - proportionality_const*(1-i+shift*(i*I))*(i)*I for i in regions]
                    difference = [0]*len(regions)
                    for i in range(0, len(regions)):
                        difference[i] = regions_year2[i] - regions[i]
                    print(f'Country total in input year {year_to_forecast-1} is {country_total_input_year}\n Country total in forecasted year {year_to_forecast} is {country_total_forecasted_year}\n Country total change is {country_total_change}\n Overall growth is {sum(difference)/I}')
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