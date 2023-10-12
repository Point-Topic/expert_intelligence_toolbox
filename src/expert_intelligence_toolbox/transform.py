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
    
    nuts_id_2021 = input_df.loc[(input_df['reported_at'] == year_to_restate) & (input_df['country_code'] == f'{country_code}')]['nuts_id_2021'].values.tolist()
    regions_y1 = input_df.loc[(input_df['reported_at'] == year_to_restate) & (input_df['country_code'] == f'{country_code}')][f'{metric_percent}'].values.round(4).tolist()
    regions_pop = input_df.loc[(input_df['reported_at'] == year_to_restate) & (input_df['country_code'] == f'{country_code}')][f'pop_{year_to_restate}'].values.round(4).tolist()
    regions_y1_abs = [regions_y1[i] * regions_pop[i] for i in range(len(regions_y1))]

    country_total_original = country_totals_df.loc[(country_totals_df['reported_at'] == year_to_restate) & (country_totals_df['country_code'] == f'{country_code}')][f'{metric_percent}'].values[0]
    country_total_restated = restated_country_totals_df.loc[(restated_country_totals_df['reported_at'] == year_to_restate) & (restated_country_totals_df['country_code'] == f'{country_code}')][f'{metric_percent}'].values[0]
    country_wide_change = float(country_total_restated - country_total_original)
    country_wide_change_abs = country_wide_change * sum(regions_pop)

    print('country_total_original is ...',country_total_original)
    print('country_total_restated is ...',country_total_restated)
    print('country_wide_change is ...',country_wide_change)
    if np.isnan(country_wide_change):
        print(f"country_wide_change is nan. Metric {metric} likely does not exist for this year {year_to_restate}, or there is a problem")

    def validate_incr(increase):
        """
        If the average percentage increase needed to make all coverage equals to 1, 
        smaller than the percentage increase --> error

        Fro example, we have [0.9, 0.5, 0.1], then the total increment needed to make 
        them fully coveraged means [1, 1, 1] > 0.5 isn't reasonable. 

        Therefore the country_change > 0.5 isn't reasonable. 
        """
        if country_wide_change >= 0:
            increase_limit = sum(regions_pop) - sum(regions_y1_abs)
        elif country_wide_change < 0:
            increase_limit = sum(regions_y1_abs)
        elif np.isnan(country_wide_change):
            increase_limit = 0
            pass # metric does not exist for this year, so we don't need to validate the increase
            

        if abs(country_wide_change_abs) > increase_limit:
            print("Invalid percentage increase")
            print('increase_limit is ',increase_limit)
            print('country_wide_change_abs is',abs(increase))
            raise(ValueError)
        elif abs(country_wide_change_abs) == increase_limit:
            if country_wide_change_abs > 0:
                print("Every region is fully covered")
            # No more coverage
            print("No more coverage")
        
        print('percentage increase validation passed.')

    # # Validate percentage increase
    validate_incr(increase=country_wide_change)

    if country_wide_change >= 0:
        regions_y1 = [0.01 if coverage == 0 else coverage for coverage in regions_y1]
        # since regions_y1 was recalculated, we need to recalculate regions_y1_abs as well
        regions_y1_abs = [regions_y1[i] * regions_pop[i] for i in range(len(regions_y1))]

    if country_wide_change < 0:
        regions_y1 = [0.99 if coverage == 1 else coverage for coverage in regions_y1]
        # since regions_y1 was recalculated, we need to recalculate regions_y1_abs as well
        regions_y1_abs = [regions_y1[i] * regions_pop[i] for i in range(len(regions_y1))]
        

    ## Processing
    total_increment = country_wide_change_abs

    # split into 12 equal chunks (distributing increase)
    number_of_chunks = 12
    total_increment_chunk = total_increment / number_of_chunks

    regions_in = regions_y1
    regions_in_abs = regions_y1_abs

    for chunk in range(number_of_chunks):
        # this part we still do using percent
        if country_wide_change >= 0:
            rate_incr = [(1 - region_coverage) * region_coverage for region_coverage in regions_in]
        elif country_wide_change < 0:
            rate_incr = [-(1 - region_coverage) * region_coverage for region_coverage in regions_in]
        elif np.isnan(country_wide_change):
            rate_incr = [0] * len(regions_in)
        
        rate_incr_sum = np.abs(np.sum(rate_incr))
        incr_weights = [i / rate_incr_sum for i in rate_incr]
        pop_weights = [i / sum(regions_pop) for i in regions_pop]

        # proportional to both rate_incr (position on bell curve) and population of region 
        chunk_allocation_weights = np.abs([incr_weights[i] * pop_weights[i] for i in range(len(incr_weights))])
        chunk_allocation_weights_sum = sum(chunk_allocation_weights)

        # change per region
        regions_change_abs = [total_increment_chunk * chunk_allocation_weights[i]/chunk_allocation_weights_sum for i in range(len(regions_in_abs))]
        
        # calc regions out
        regions_out_abs = [regions_in_abs[i] + regions_change_abs[i] for i in range(len(regions_in_abs))]

        # we now apply the rate_incr to the absolute regions
        regions_out = [regions_out_abs[i] / regions_pop[i] for i in range(len(regions_out_abs))]

        while len([1 for coverage in regions_out if coverage > 1 or coverage < 0]) != 0:
            print('Some regions coverage are above 1 or below 0. Adding post-processing iteration.')
            
            if country_wide_change >= 0:
                excess_coverage = np.abs(sum(((regions_out_abs[index]) - regions_pop[index] for index, coverage in enumerate(regions_out) if coverage > 1)))
                print('Excess Coverage is ',excess_coverage)
                
                regions_out_abs = [1 * regions_pop[index] if coverage > 1 else regions_out[index] * regions_pop[index] for index, coverage in enumerate(regions_out)]
                
                new_rate_incr_sum = np.abs(np.sum([rate_incr[index] for index, coverage in enumerate(regions_out) if coverage < 1]))
                
                new_incr_weights = [rate_incr[index]/new_rate_incr_sum if coverage < 1 else 0 for index, coverage in enumerate(regions_out)]
                
                
                new_pop_weights = [i / sum(regions_pop) for i in regions_pop] # this is unchanged

                # we are just repeating, but with different weights, so the logic from here is unchanged
                excess_allocation_weights = np.abs([new_incr_weights[i] * new_pop_weights[i] for i in range(len(new_incr_weights))])
                excess_allocation_weights_sum = sum(excess_allocation_weights)
                
                regions_change_abs = [excess_coverage * excess_allocation_weights[i]/excess_allocation_weights_sum for i in range(len(regions_out_abs))]
                
                regions_out_abs = [regions_out_abs[i] + regions_change_abs[i] for i in range(len(regions_out_abs))]
                

                regions_out = [regions_out_abs[i] / regions_pop[i] for i in range(len(regions_out_abs))]
                
                
            elif country_wide_change < 0:
                excess_coverage = np.abs(sum(((0 - regions_out_abs[index]) for index, coverage in enumerate(regions_out) if coverage < 0)))
                print('Excess Coverage is ',excess_coverage)
                
                regions_out_abs = [0 * regions_pop[index] if coverage < 0 else regions_out[index] * regions_pop[index] for index, coverage in enumerate(regions_out)]
                #regions_out_abs = [0 if coverage < 0 else coverage for coverage in regions_out_abs]
                
                new_rate_incr_sum = np.abs(np.sum([rate_incr[index] for index, coverage in enumerate(regions_out) if coverage > 0]))

                new_incr_weights = [rate_incr[index]/new_rate_incr_sum if coverage > 0 else 0 for index, coverage in enumerate(regions_out)]
                
                new_pop_weights = [i / sum(regions_pop) for i in regions_pop] # this is unchanged

                # we are just repeating, but with different weights, so the logic from here is unchanged
                excess_allocation_weights = np.abs([new_incr_weights[i] * new_pop_weights[i] for i in range(len(new_incr_weights))])
                excess_allocation_weights_sum = sum(excess_allocation_weights)

                regions_change_abs = [excess_coverage * excess_allocation_weights[i]/excess_allocation_weights_sum for i in range(len(regions_out_abs))]

                regions_out_abs = [regions_out_abs[i] - regions_change_abs[i] for i in range(len(regions_out_abs))]

                regions_out = [regions_out_abs[i] / regions_pop[i] for i in range(len(regions_out_abs))]

        # resetting regions_in for next iteration
        regions_in = regions_out
        regions_in_abs = regions_out_abs

    # in case there is no restatement (i.e. the metric isn't tracked for that year), we want to return the original values
    if np.isnan(country_wide_change):
        regions_y2 = regions_y1
        regions_y2_abs = regions_y1_abs
    else:
        regions_y2 = regions_out
        regions_y2_abs = regions_out_abs
    
    output = {
        'nuts_id_2021': nuts_id_2021, 
        'country_code': f'{country_code}', 
        f'{metric_percent}': regions_y2, 
        f'{metric_pop}': regions_y2_abs, 
        f'pop': regions_pop,
        'reported_at': year_to_restate
        }
    output_df = pd.DataFrame(output)
    
    output_df[f'{metric_percent}'] = output_df[f'{metric_percent}'].apply(lambda x: round(x,4))

    print('Change that should have been distributed: ',country_wide_change_abs)
    print('Change that was distributed: ',sum(regions_out_abs)-sum(regions_y1_abs))
    print('Country-wide Y1 coverage as average of all regions is:',sum(regions_y1_abs)/sum(regions_pop))
    print('Country-wide Y2 coverage as average of all regions is:',sum(regions_out_abs)/sum(regions_pop))
    print('Meaning a change of :',(sum(regions_y1_abs)/sum(regions_pop))-(sum(regions_out_abs)/sum(regions_pop)))
    
    return output_df
