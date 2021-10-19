import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC
from scipy import stats
import time

class ECOTOX_data_source:
    def __init__(self, all_chemicals, all_species, all_endpoints, all_durations) -> None:
        self.all_chemicals = all_chemicals
        self.all_species  = all_species
        self.all_endpoints = all_endpoints
        self.all_durations = all_durations

    def check(self):
        assert len(self.all_species) == len(self.all_endpoints) == len(self.all_durations), '输入的物种数、毒性终点数、时长不一致'

class ECOTOX_search_condition:
    def __init__(self, chemical, species, endpoint, duration) -> None:
        self.chemical = chemical
        self.species  = species
        self.endpoint = endpoint
        self.duration = duration

    def enumerate_output(self):
        return self.species + '\t' + self.chemical + '\t' + self.endpoint + '\t' + str(self.duration) + '_Day(s)'

class ECOTOX_search_result:
    def __init__(self, selected_data, final_data) -> None:
        self.selected_data = selected_data
        self.final_data = final_data

class ECOTOX_chrome_driver:
    def __init__(self) -> None:
        option = webdriver.ChromeOptions()
        # 隐藏窗口
        # option.add_argument('headless')
        # 防止打印一些无用的日志
        option.add_experimental_option(
            "excludeSwitches", ['enable-automation', 'enable-logging'])
        
        self.driver = webdriver.Chrome(options=option)
        self.driver.get('https://cfpub.epa.gov/ecotox/search.cfm')

        # 第一次进行搜索
        self.first_time_search = True
        # 第一次搜索到数据
        self.first_time_success = True

    # 收集一次数据
    def collect_once(self, search_condition: ECOTOX_search_condition):
        self.search_condition = search_condition
        # 查询词条装载
        self.data_onload()
        # 数据选择与处理(如果数据存在)
        self.selected_data = []
        self.final_data = format(0, '.5f')
        if self.data_isExisted():
            self.data_select()
            self.data_process()

        # 第一次查询结束的标志
        self.first_time_search = False

        return ECOTOX_search_result(self.selected_data, self.final_data)
    
    # ------------------------------
    # collect_once() 内各个步骤
    # ------------------------------
    # 装载数据
    def data_onload(self):
        self.set_chemical(self.search_condition.chemical)
        if self.first_time_search:
            self.set_endpoint()
        self.set_speices(self.search_condition.species)
        self.submit()
        if self.first_time_success:
            if self.data_isExisted():
                self.set_data_length(100)
        if self.data_isExisted():
            self.wait_for_data_refresh()
        
    # 判断数据是否存在
    def data_isExisted(self):
        # 小贴士: 如果在until中自定义判断条件
        # until里要传入的是一个判断函数而非判断本身, 函数的参数为driver
        # wait.py中写道, 判断函数给的东西是true, 那么会返回传入的东西

        # 判断提交按钮是否还可见
        WebDriverWait(self.driver, 10).until_not(
            EC.visibility_of_element_located((By.XPATH, "//button[@data-handler='runSearch']"))
        )
        data_count_text = self.driver.find_element(By.XPATH, "//h2[@id='recordCount-results']").text

        return data_count_text != '0 results'

    # 选择合法数据
    def data_select(self):
        # 数据存在table->tbody->tr中
        data_table_tbody = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//table[@id='searchResultsDataTable']/tbody"))
        )
        data_table_tbody_tr = data_table_tbody.find_elements(By.XPATH, "./tr")

        # 提取数据
        for tr in data_table_tbody_tr:
            # 对于每个tr, 准备截取数据
            tds = tr.find_elements(By.XPATH, "./td")
            target_endpoint = tds[15].text
            target_duration = tds[17].text
            target_data = tds[12].text[tds[12].text.find('\n') + 1:]  # 记得+1

            end = 0

            # 判断毒性终点
            # 判断时长
            # 判断毒性数据是否合法(如为 ">" 或 "~" 则不要)
            # 单位是否合法
            if target_endpoint == self.search_condition.endpoint or self.search_condition.endpoint + '*':
                if target_duration == str(self.search_condition.duration) + ' Day(s)':
                    if target_data[0].isdigit():
                        if target_data.find('mg/L') != -1:
                            end = target_data.find(' ')

            if end > 0:
                self.selected_data.append(float(target_data[:end]))
        
    # 处理数据
    def data_process(self):
        if len(self.selected_data):
            self.final_data = format(stats.gmean(self.selected_data), '.5f')

    # ------------------------------
    # data_onload() 相关详细函数
    # ------------------------------
    # 化合物
    def set_chemical(self, chemical):
        button_Chemicals = self.driver.find_element(By.XPATH, "//div[@data-search-param='Chemicals']/button")
        button_Chemicals.click()
        text_area_Chemicals = self.driver.find_elements(By.TAG_NAME, 'textarea')[0]
        text_area_Chemicals.clear()
        text_area_Chemicals.send_keys(chemical)
        time.sleep(1) # 等待输入完毕

    # 毒性终点
    def set_endpoint(self):
        button_Endpoints = self.driver.find_element(By.XPATH, "//div[@data-search-param='Endpoints']/button")
        button_Endpoints.click()
        time.sleep(1)  # 有个动画, 等框出现
        endPoint_LC50 = self.driver.find_element(By.XPATH, "//label[@for='cbResultsGroup12a']")
        endPoint_LC50.click()
        endPoint_EC50 = self.driver.find_element(By.XPATH, "//label[@for='cbResultsGroup13a']")
        endPoint_EC50.click()

    # 物种
    def set_speices(self, species):
        button_Species = self.driver.find_element(By.XPATH, "//div[@data-search-param='Species']/button")
        button_Species.click()
        text_area_species = self.driver.find_elements(By.TAG_NAME, 'textarea')[2]
        text_area_species.clear()
        text_area_species.send_keys(species)
        time.sleep(1) # 等待输入完毕

    # 提交
    def submit(self):
        WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//button[@data-handler='runSearch']"))
        ).click()

    # 每一页显示100条
    def set_data_length(self, value:int):
        Select(
            WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//select[@name='searchResultsDataTable_length']"))
            )
        ).select_by_value(str(value))

    # 等待数据刷新
    def wait_for_data_refresh(self):
        if self.first_time_success:
            WebDriverWait(self.driver, 10).until(
                EC.staleness_of(self.driver.find_element(By.XPATH, "//table[@id='searchResultsDataTable']/tbody/tr"))
            )
            self.first_time_success = False
        else:
            # 是否存在有几条数据的信息已经发过来, 但是数据本身还没发过来的情况?
            time.sleep(1)

def ECOTOX_collect_all_data_and_document(data_source: ECOTOX_data_source):
    driver = ECOTOX_chrome_driver()

    log_file = open('log_file.txt','a')
    result_file = open('result_file.txt', 'a')

    for species_index in range(0, len(data_source.all_species)):
        for chemical_index in range(0, len(data_source.all_chemicals)):
            # 查找
            sc = ECOTOX_search_condition(
                data_source.all_chemicals[chemical_index],
                data_source.all_species[species_index],
                data_source.all_endpoints[species_index],
                data_source.all_durations[species_index],
            )
            sr = driver.collect_once(sc)

            # 记录
            log_file.write(sc.enumerate_output() + '\t' + sr.final_data + '\t' + str(sr.selected_data) + '\n')
            result_file.write(sr.final_data + '\t')
            if (chemical_index + 1) % len(data_source.all_chemicals) == 0:
                result_file.write(sc.species + '\n')
    
    log_file.close()
    result_file.close()


def main():
    ds = ECOTOX_data_source(
        # 化合物
        ['DDT', 'hexachlorobenzene', 'heptachlor'],
        # 物种(学名)
        ['Lepomis', 'Bufo'],
        # 毒性终点
        ['LC50', 'LC50'],
        # 时间长度(天)
        [4, 1]
    )

    # 检查源数据是否合规
    ds.check()

    # 收集所有数据并存储
    ECOTOX_collect_all_data_and_document(ds)

if __name__ == "__main__":
    main()
