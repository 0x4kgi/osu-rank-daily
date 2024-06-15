from datetime import datetime
from scripts.json_player_data import (
    MappedPlayerDataCollection,
    MappedScoreData,
    MappedScoreDataCollection,
    get_comparison_and_mapped_data,
    get_data_at_date,
    get_sorted_dict_on_stat,
    map_player_data
)

import argparse
import scripts.general_utils as util
import scripts.html_utils as html

def generate_html_from_player_data(
    data:MappedPlayerDataCollection, 
    data_difference:MappedPlayerDataCollection = None,
    timestamp:float = 0.0, 
    test:bool = False,
    output_file:str = 'docs/index.html',
) -> str:
    rows = ''
    
    def td(td) -> str:
        return html.elem('td', td)
    
    def avatar(user_id) -> str:
        image = html.elem(tag_name='img', **{
            'src': f'https://a.ppy.sh/{user_id}',
            'loading': 'lazy'
        })
        return td(image)
    
    def difference_td(id, stat) -> str:
        if data_difference is None:
            return td(data[id].get(stat))
        
        current = data[id].get(stat)
        compare = data_difference[id].get(stat, 0)
        
        if stat in ['acc', 'pp']:
            compare = round(compare, 2)
        
        change = ''
        if compare:
            change = html.elem('sup',
                '+' if compare > 0 else '',
                str(compare),
                **{
                    'class': 'increase' if compare > 0 else 'decrease'
                }
            )
        
        if stat in ['acc']:
            return td(f'{current:.2f}%{change}')
        else:
            return td(f'{current:,}{change}')
    
    for user_id in data:
        tr_class_list = []

        pic = avatar(user_id)
        rank = difference_td(user_id, 'country_rank')
        ign = td(data[user_id]['ign'])
        pp = difference_td(user_id, 'pp')
        acc = difference_td(user_id, 'acc')
        pc = difference_td(user_id, 'play_count')
        x = difference_td(user_id, 'rank_x')
        s = difference_td(user_id, 'rank_s')
        a = difference_td(user_id, 'rank_a')
        
        if data_difference[user_id]['new_entry']:
            tr_class_list.append('new-entry')
        
        if data_difference[user_id]['country_rank'] > 0:
            tr_class_list.append('rank-up')
        elif data_difference[user_id]['country_rank'] < 0:
            tr_class_list.append('rank-down')
        
        rows += html.table_row(
            rank, pic, ign, pp, acc, pc, x, s, a,
            **{
                # TODO: this is ew, if possible clean this up, ty
                'class': ' '.join(tr_class_list) if len(tr_class_list) else None
            }
        ) + '\n'
    
    formatted_time = util.timestamp_utc_offset(
        timestamp=timestamp,
        time_offset=8,
        time_format="%Y-%m-%d %H:%M:%S"
    )
    
    def total_stat(data, key) -> int:
        return sum([data[i][key] for i in data if data[i][key] > 0])
    
    # what the fuck
    # get_sorted_dict_on_stat returns a dict
    # but you cannot get_sorted_dict_on_stat().items()[0] this
    # so to get the first element, cast it to a list and since an element is a tuple
    # discard the first since its just the user_id and we only need the dict
    # and then just do normal dict[key] to get relevant values
    # unsure if this will die if some random bullshit happens, we will see
    _, top_pp_gain = list(get_sorted_dict_on_stat(data_difference, 'pp', True).items())[0]
    _, top_pc_gain = list(get_sorted_dict_on_stat(data_difference, 'play_count', True).items())[0]
    _, top_rank_gain = list(get_sorted_dict_on_stat(data_difference, 'country_rank', True).items())[0]
    
    # TODO: i dont like how this ended up at all, clean up please
    # IT LOOKS SO BAD!!
    replacements = {
        'updated_at': formatted_time,
        'pp_gain': '{:,}'.format(round(top_pp_gain.get('pp', -1))),
        'pp_name': top_pp_gain.get('ign', 'nobody'),
        'rank_gain': '{:,}'.format(top_rank_gain.get('country_rank', -1)),
        'rank_name': top_rank_gain.get('ign', 'nobody'),
        'pc_gain': '{:,}'.format(top_pc_gain.get('play_count', -1)),
        'pc_name': top_pc_gain.get('ign', 'nobody'),
        'pp_total': round(total_stat(data_difference, 'pp'), 2),
        'pc_total': '{:,}'.format(total_stat(data_difference, 'play_count')),
        'rows': rows,
    }
    
    return stuff_to_html_templates(
        template='docs/main-page.template.html',
        output_path=output_file,
        test=test,
        **replacements,
    )

def gather_player_data(
    base_date = datetime.now(),
    compare_date_offset = 1,
    output_file = 'docs/index.html',
    country = 'PH',
    mode = 'fruits',
    test = False,
) -> None:
    processed_data = get_comparison_and_mapped_data(base_date, compare_date_offset, country, mode, test)
    latest_mapped_data = processed_data.latest_mapped_data
    comparison_mapped_data = processed_data.comparison_mapped_data
    data_difference = processed_data.data_difference
    latest_data_timestamp = processed_data.latest_data_timestamp
    
    if latest_mapped_data is None:
        print('Cannot get latest data as of now.')
        return
    
    if comparison_mapped_data is None:
        print('Cannot get comparison data as of now.')
        return
    
    file_name = generate_html_from_player_data(
        data=latest_mapped_data, 
        data_difference=data_difference,
        test=test, 
        timestamp=latest_data_timestamp,
        output_file = output_file,
    )
    
    print(file_name)

def make_players_list_page(
    country: str = 'PH',
    mode: str = 'fruits',
    option: str = 'yesterday',
    test: bool = False
) -> None:
    options = {
        # (timedelta, file_name_output)
        # TODO: make the base dir only a single instance
        'yesterday': (1, 'docs/index.html'),
        'week': (7, 'docs/weekly.html'),
        'month': (30, 'docs/monthly.html'),
        'year': (365, 'docs/yearly.html'),

        # TODO: compare from start of month, year, etc..
    }

    day_offset, output_file = options.get(option, None)

    if day_offset is None:
        print('Pick a valid option. [yesterday, week, monthly]')
        return

    gather_player_data(
        base_date=datetime.now(),
        compare_date_offset=day_offset,
        country=country, mode=mode, test=test,
        output_file=output_file
    )

def stuff_to_html_templates(
    template: str,
    output_path: str,
    test: bool,
    **variables,
) -> str:
    if test:
        output_path = 'tests/' + output_path
    
    output_file = html.create_page_from_template(
        template_path=template,
        output_path=output_path,
        **variables
    )
    
    return output_file

def generate_html_from_pp_data(
    data: MappedScoreDataCollection,
    test: bool = False,
) -> None:
    def td(content):
        return html.elem('td', str(content))
    
    rows = []
    
    for i in data:
        # im too lazy to type more
        d: MappedScoreData = data[i]
        
        pp = td(d['score_pp'])
        player = td(d['user_name'])
        song = td(d['beatmapset_title'])
        diff = td(d['beatmap_version'])
        sr = td(d['beatmap_difficulty'])
        acc = td(round(d['accuracy'] * 100))
        miss = td(d['count_miss'])
        mods = td(d['score_mods'])
        
        rows.append(html.table_row(
            pp,player,song,diff,sr,acc,miss,mods
        ))
    
    return stuff_to_html_templates(
        template='docs/pp-list.template.html',
        output_path='docs/pp-rankings.html',
        test=test,
        title='PP rankings for the day',
        rows='\n'.join(rows),
    )
    
def make_pp_records_page(
    country: str = 'PH',
    mode: str = 'fruits',
    test: bool = False,
) -> None:
    latest_timestamp = datetime.now()
    
    raw_scores = get_data_at_date(
        date=latest_timestamp.strftime('%Y/%m/%d'),
        country=country,
        mode=mode,
        file_type='pp-records',
        test=test,
    )
    
    if raw_scores is None:
        print('Cannot get pp score list at the moment.')
        return
    
    mapped_scores: MappedScoreDataCollection = map_player_data(raw_scores)
    
    generate_html_from_pp_data(data=mapped_scores, test=test)

def run(
    country: str = 'PH',
    mode: str = 'fruits',
    option: str = 'yesterday',
    test: bool = False,
    skip_list: bool = False,
    skip_pp: bool = False,
) -> None:
    
    if not skip_list:
        make_players_list_page(
            country=country,
            mode=mode,
            option=option,
            test=test
        )
    else:
        print('Skipping making the player list.')
    
    if not skip_pp:
        make_pp_records_page(
            country=country,
            mode=mode,
            test=test
        )
    else:
        print('Skipping making the pp records list.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate page from fetched data, requires leaderboard_scrape.py to be ran first!')
    
    parser.add_argument('--mode', type=str, default='fruits', help='Define what mode, uses the parameters used on osu site.')
    parser.add_argument('--country', type=str, default='PH', help='What country to make a page from. Uses 2 letter country codes.')
    parser.add_argument('--range', type=str, default='yesterday', help='What would be the comparison date to be done.')
    parser.add_argument('--test', action='store_true', help='Just do tests')
    parser.add_argument('--skip-list', action='store_true')
    parser.add_argument('--skip-pp', action='store_true')
    
    args = parser.parse_args()
    
    run(
        country=args.country,
        mode=args.mode,
        option=args.range,
        test=args.test,
        skip_list=args.skip_list,
        skip_pp=args.skip_pp
    )