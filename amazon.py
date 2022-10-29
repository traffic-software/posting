from xml.dom.minidom import Element
import mysql.connector
from selenium import webdriver
import time
driver = webdriver.Firefox(
    executable_path=r'/home/los3r/Desktop/geckodriver')

driver.get('https://www.amazon.com/Krylon-K02203-General-Purpose-Metallic/dp/B0042T7TRC/ref=cm_cr_arp_d_product_top?ie=UTF8&th=1')
time.sleep(10)

##products Table start done
productsname=driver.find_element_by_xpath("//span[@id='productTitle']").text
productsreview_count=driver.find_element_by_xpath("//span[@id='acrCustomerReviewText']").text
productsreview_average=driver.find_element_by_xpath('//span[@data-hook="rating-out-of-text"]').text
productsDescription=driver.find_element_by_xpath("//div[@id='productDescription_feature_div']").text
productsurl=driver.current_url    
try:
   productsprice=driver.find_element_by_xpath('//span[@class="a-price aok-align-center reinventPricePriceToPayMargin priceToPay"]').text
except:
   productsprice="00.0"    

productscatagory=driver.find_element_by_xpath('//ul[@class="a-unordered-list a-horizontal a-size-small"]//child::li[1]').text
store=driver.find_element_by_xpath('//a[@id="bylineInfo"]')
store.click()
productsstore_url = driver.current_url
time.sleep(5)
productsstore_name=driver.find_element_by_xpath('//span[@itemprop="item"]').text
productsstore_logo=driver.find_element_by_xpath('//div[@class="Header__leftColumn__1BAI2"]//child::img').get_attribute('src')
driver.back()
time.sleep(5)

###products Table end

###product_info Table start
i= 1
#product_infoid=productsid
#product_infoproduct_id=
product_infoname1=driver.find_element_by_xpath('(//table[@id="productDetails_techSpec_section_1"]//child::th)[1]').text
product_infoname2=driver.find_element_by_xpath('(//table[@id="productDetails_techSpec_section_1"]//child::th)[2]').text
product_infoname3=driver.find_element_by_xpath('(//table[@id="productDetails_techSpec_section_1"]//child::th)[3]').text
product_infoname4=driver.find_element_by_xpath('(//table[@id="productDetails_techSpec_section_1"]//child::th)[4]').text
product_infoname5=driver.find_element_by_xpath('(//table[@id="productDetails_techSpec_section_1"]//child::th)[5]').text

product_infoname= product_infoname1,product_infoname2,product_infoname3,product_infoname4,product_infoname5

# product_infoname_count = len(driver.find_elements_by_xpath('(//table[@id="productDetails_techSpec_section_1"]//child::th)'))
# while i < product_infoname_count:
#     product_infoname_f=driver.find_element_by_xpath('(//table[@id="productDetails_techSpec_section_1"]//child::th)[{i}]').text
#     print(i,product_infoname_f)
#     if i == (product_infoname_count):
#         break
#     i +=1
        
product_infovalue1=driver.find_element_by_xpath('(//table[@id="productDetails_techSpec_section_1"]//child::td)[5]').text
product_infovalue2=driver.find_element_by_xpath('(//table[@id="productDetails_techSpec_section_1"]//child::td)[2]').text
product_infovalue3=driver.find_element_by_xpath('(//table[@id="productDetails_techSpec_section_1"]//child::td)[3]').text
product_infovalue4=driver.find_element_by_xpath('(//table[@id="productDetails_techSpec_section_1"]//child::td)[4]').text
product_infovalue5=driver.find_element_by_xpath('(//table[@id="productDetails_techSpec_section_1"]//child::td)[5]').text

product_infovalue = product_infovalue1,product_infovalue2,product_infovalue3,product_infovalue4,product_infovalue5


# for x in range(0,product_infoname_count):
#     product_infovalue_f=driver.find_element_by_xpath('(//table[@id="productDetails_techSpec_section_1"]//child::td)[1]').text

###product_info Table end
###images Table start

#imagesid=productsid
#imagesproduct_id=product_id
imagesurl=driver.find_element_by_xpath('//span[@id="a-autoid-4-announce"]//child::img').get_attribute('src')
###images Table end


###reviews Table start

review=driver.find_element_by_xpath('(//a[@data-hook="see-all-reviews-link-foot"])')
review.click()
time.sleep(5)
review_count=len(driver.find_elements_by_xpath('(//div[@data-hook="review"])'))
### replace 0 to review_count in for loop###
for x in range(0,review_count):
    #reviewsid=
    #reviewsproduct_id=productsid

    try:
        reviewshelpful=driver.find_element_by_xpath('(//span[@class="a-size-base a-color-tertiary cr-vote-text"])[1]').text
    except:
        reviewshelpful=("NOt Helpfull")
            
    reviewsuser_name=driver.find_element_by_xpath('(//span[@class="a-profile-name"])[1]').text
    reviewscountry_name=driver.find_element_by_xpath('(//span[@class="a-size-base a-color-secondary review-date"])[1]').text
    reviewsdate=driver.find_element_by_xpath('(//span[@class="a-size-base a-color-secondary review-date"])[1]').text
    reviewstext=driver.find_element_by_xpath('(//span[@class="a-size-base review-text review-text-content"]//child::span)[1]').text
    reviewsstars=driver.find_element_by_xpath('(//i[@data-hook="review-star-rating-view-point" or @data-hook="review-star-rating"]//child::span)[1]').text
    reviewsuser_url=driver.find_element_by_xpath('(//a[@class="a-profile"])[1]')
    reviewsuser_url.click()
    time.sleep(5)
    reviewsuser_img=driver.find_element_by_xpath('//img[@id="avatar-image"]').get_attribute('src')
    print(reviewsuser_img)
    time.sleep(5)
    driver.back()
driver.back()

###reviews Table end

###question Table start
ques_count=len(driver.find_elements_by_xpath('//div[@class="a-fixed-left-grid a-spacing-small" and contains(@id, "question-")]'))
for x in range(0,ques_count):
    # questionid=
    # questionproduct_id=productsid
    questionvotes=00
    questionquestion=driver.find_element_by_xpath('(//a[@class="a-link-normal"]//child::span[@data-action="ask-log-click-csm"])[1]').text
    print(questionquestion)

###question Table end

###answers Table start

for x in range(0,ques_count):
    #answersid=
    #answersquestion_id=
    
    ### answerstext value always x+1
    
    answerstext=driver.find_element_by_xpath('(//div[@class="a-fixed-left-grid-col a-col-right" and @style="padding-left:0%;float:left;"])[2]').text
    answersdate=driver.find_element_by_xpath('(//span[@class="a-color-tertiary a-nowrap"])[1]').text
    print(answerstext)
    answersuser_name=answersdate
    answershelpful="yes"

###answers Table end

mydb = mysql.connector.connect(
   host = "localhost",
   user = "mysql",
   password = "loser@",
   database = "project"
   )
mycursor = mydb.cursor()

sqlproducts="Insert into products(name,review_count,review_average,Description,url,price,store_name,store_url,store_logo,catagory) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
sqlproducts_value=[(productsname,productsreview_count,productsreview_average,productsDescription,productsurl,productsprice,productsstore_name,productsstore_url,productsstore_logo,productscatagory)]

# sqlproduct_info="Insert into product_info(type,name,value) values(%s,%s,%s)"
# sqlproduct_info_value=[(productsname,product_infoname_f,product_infovalue_f)]

sqlimages="Insert into products(url) values(%s)"
sqlimages_value=[(imagesurl)]

for x in range(0,review_count):      
   sqlreviews="Insert into products(helpful,user_name,country_name,date,user_url,text,stars,user_img) values(%s,%s,%s,%s,%s,%s,%s,%s)"
   sqlreviews_value=[(reviewshelpful,reviewsuser_name,reviewscountry_name,reviewsdate,reviewsuser_url,reviewstext,reviewsstars,reviewsuser_img)]

for x in range(0,ques_count):
   sqlquestion="Insert into products(votes,question) values(%s,%s)"
   sqlquestion_value=[(questionvotes,questionquestion)]

for x in range(0,ques_count):
   sqlanswers="Insert into products(text,date,user_name,helpful) values(%s,%s,%s,%s)"
   sqlanswers_value=[(answerstext,answersdate,answersuser_name,answershelpful)]

mycursor.executemany(sqlproducts,sqlproducts_value)

mydb.commit()