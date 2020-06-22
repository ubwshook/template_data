package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"net/url"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/chromedp/cdproto/page"
	"github.com/chromedp/chromedp"
)

const DevtoolsUrl string = "http://localhost:9222"
const OnePartition int = 10
const testMaxPage int = 30

type table map[string]string

type Content struct {
	MedicId string
	Type string
	Content string
	Page int
}

type ChromeHeadlessInfo struct {
	Browser                string   `json:"Browser"`
	ProtocolVersion        string   `json:"Protocol-Version"`
	UserAgent              string   `json:"User-Agent"`
	V8Version              string   `json:"V8-Version"`
	WebKitVersion          string   `json:"WebKit-Version"`
	WebSocketDebuggerUrl   string   `json:"webSocketDebuggerUrl"`
}

func getDevtoolsWsUrl(host string) string {
	getUrl := fmt.Sprintf("%s/json/version", host)

	client := &http.Client{Timeout: 5 * time.Second}
	resp, err := client.Get(getUrl)
	if err != nil {
		panic(err)
	}
	defer resp.Body.Close()

	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		fmt.Println(err)
	}

	var info ChromeHeadlessInfo
	err2 := json.Unmarshal(body, &info)
	if err2 != nil {
		panic(err2.Error())
	}

	fmt.Println(info.WebSocketDebuggerUrl)
	return info.WebSocketDebuggerUrl
}

func getCurrentPageNumber(ctx context.Context) int {
	var content string
	if err := chromedp.Run(ctx, chromedp.Text(`#content`, &content, chromedp.NodeVisible, chromedp.ByID)); err != nil {
		log.Printf("could not get content: %v.\n", err)
	}
	//fmt.Println(content)
	re := regexp.MustCompile(`第\s[0-9]+\s页`)
	pageNow := re.FindString(content)
	pageNow = strings.TrimLeft(pageNow, "第")
	pageNow = strings.TrimRight(pageNow, "页")
	pageNow = strings.TrimSpace(pageNow)

	pageNowInt, err := strconv.Atoi(pageNow)
	if err != nil {
		fmt.Println("Failed to get current page number from: ", pageNow)
		return 0
	}
	//fmt.Println("Get now page number: ", pageNowInt)
	return pageNowInt
}

func parseMaxNumber(content string) int {
	re := regexp.MustCompile(`共[0-9]+页`)
	pageMax := re.FindString(content)
	pageMax = strings.TrimLeft(pageMax, "共")
	pageMax = strings.TrimRight(pageMax, "页")
	pageMax = strings.TrimSpace(pageMax)

	pageMaxInt, err := strconv.Atoi(pageMax)
	if err != nil {
		fmt.Println("Failed to get max page number from: ", pageMax)
		return 0
	}
	fmt.Println("Get max page number: ", pageMaxInt)
	return pageMaxInt
}

func getMaxPageNumber(ctx context.Context) int {
	var content string
	if err := chromedp.Run(ctx, chromedp.Text(`#content`, &content, chromedp.NodeVisible, chromedp.ByID)); err != nil {
		log.Printf("could not get content: %v.\n", err)
	}
	//fmt.Println(content)
	return parseMaxNumber(content)
}

func getUrlStartPage(currentUrl string) int {
	u, err := url.Parse(currentUrl)
	if err != nil {
		panic(err)
	}

	m, _ := url.ParseQuery(u.RawQuery)
	startPage := m["startPage"]

	startPageInt, err := strconv.Atoi(startPage[0])
	if err != nil {
		fmt.Println("Failed to get start page number from: ", startPage)
		return 1
	}

	return startPageInt
}

func devPage(ctx context.Context, target int) bool {
	// eval the go Page js
	jsCode := fmt.Sprintf("devPage(%d)", target)
	if err := chromedp.Run(ctx, chromedp.Evaluate(jsCode, new(string))); err != nil {
	}

	// wait new content load
	if err := chromedp.Run(ctx, chromedp.WaitEnabled(`#goInt`)); err != nil {
	}

	// check if the eval success
	pageNow := getCurrentPageNumber(ctx)
	if pageNow == target {
		return true
	}else{
		return false
	}
}

func printPageTitle(ctx context.Context) {
	// get the page title
	var title string
	if err := chromedp.Run(ctx, chromedp.Title(&title)); err != nil {
		log.Printf("could not get page title: %v", err)
	}
	fmt.Println(title)
}

func openFirstPage(ctx context.Context, url string) {
	// Disable the window.navigate.webdriver flag.
	err := chromedp.Run(ctx, chromedp.ActionFunc(func(cxt context.Context) error {
		_, err := page.AddScriptToEvaluateOnNewDocument("Object.defineProperty(navigator, 'webdriver', { get: () => false, });").Do(cxt)
		if err != nil {
			return err
		}
		return nil
	}))
	if err != nil {
		fmt.Println(err)
	}

	// navigate
	currentUrl := url
	if err := chromedp.Run(ctx, chromedp.Navigate(currentUrl),
		chromedp.WaitVisible(`#pageForm`, chromedp.ByID),
	); err != nil {
		log.Printf("could not navigate to first search list: %v", err)
	}
}

func getCurrentType(ctx context.Context) string {
	var content string
	if err := chromedp.Run(ctx, chromedp.Text(`#content`, &content, chromedp.NodeVisible, chromedp.ByID)); err != nil {
		log.Printf("could not get content: %v", err)
	}
	//fmt.Println(content)
	re := regexp.MustCompile(`".+"`)
	typeNow := re.FindString(content)
	typeNow = strings.Trim(typeNow, "\"")
	typeNow = strings.TrimSpace(typeNow)

	return typeNow
}

type medicine struct {
	Id string
	Type string
	Content string
	Page int
}

func formatDetailInfo(db *gorm.DB, content string, medicId string, currentType string, pagePoint int) {
	medic := medicine{}
	medic.Id = medicId
	medic.Content = content

	medic.Page = pagePoint
	medic.Type = currentType
	//fmt.Println(medic)
	re := regexp.MustCompile(`\n[^\n]+名称[^\n]+\n`)
	showContent := re.FindString(content)
	showContent = strings.TrimSpace(showContent)

	fmt.Printf("Id:%s, Type:%s, %s, Page:%d.\n",medic.Id, medic.Type, showContent,medic.Page)

	//TODO,Just test.
	//medic.Content = strings.Split(content, "\n")[3]
	//fmt.Println(medic.Content)

	//输出格式
	fmt.Println("Success to get one result. :", medic.Id)
	var contentDb = Content{MedicId:medic.Id, Type:medic.Type, Content:medic.Content, Page:medic.Page}
	db.Table(resTableName).Create(&contentDb)
	//fmt.Println(map[int]interface{}{
	//	0: medic.Id,
	//	1: medic.Type,
	//	2: medic.Content,
	//	3: medic.Page,
	//})
}

func getDetailInfo(ctx context.Context, db *gorm.DB, code string, medicId string, currentType string, pagePoint int) bool {
	// eval the go Page js
	if err := chromedp.Run(ctx, chromedp.Evaluate(code, new(string))); err != nil {
	}
	// wait new content load
	if err := chromedp.Run(ctx, chromedp.WaitVisible(`#content td[onclick="javascript:viewList();"]`)); err != nil {
	}

	var content string
	if err := chromedp.Run(ctx, chromedp.Text(`#content`, &content, chromedp.NodeVisible, chromedp.ByID)); err != nil {
		log.Printf("could not get content: %v", err)
	}
	//fmt.Println(content)
	formatDetailInfo(db, content, medicId, currentType, pagePoint)

	if err := chromedp.Run(ctx, chromedp.Evaluate(`viewList()`, new(string))); err != nil {
	}
	// wait new content load
	if err := chromedp.Run(ctx, chromedp.WaitVisible(`#goInt`)); err != nil {
	}
	// check if the eval success
	pageNow := getCurrentPageNumber(ctx)
	if pageNow == pagePoint {
		return true
	}else{
		return false
	}
}

func getDetailContent(ctx context.Context, db *gorm.DB, idList [15]string) {
	//content := make(map[string]string)
	var contentList []map[string]string
	if err := chromedp.Run(ctx, chromedp.AttributesAll(`#content a`, &contentList, chromedp.NodeVisible, chromedp.ByID, chromedp.ByQueryAll)); err != nil {
		log.Printf("could not get content: %v", err)
	}

	currentPage := getCurrentPageNumber(ctx)
	currentType := getCurrentType(ctx)

	for index, value := range contentList {
		//fmt.Println(value)
		jsCode := strings.Split(value["href"], ":")[1]
		getDetailInfo(ctx, db, jsCode, idList[index], currentType, currentPage)
		time.Sleep(1 * time.Second)
	}
}

func getContent(ctx context.Context, db *gorm.DB) {
	var content string
	if err := chromedp.Run(ctx, chromedp.Text(`#content`, &content, chromedp.NodeVisible, chromedp.ByID)); err != nil {
		log.Printf("could not get content: %v", err)
	}
	//fmt.Println(content)
	re := regexp.MustCompile(`[0-9]+\..+\s(.+)`)
	contentList := re.FindAllString(content, 15)
	var idList [15]string
	for index, value := range contentList {
		//fmt.Println(value)

		s1 := strings.Split(value, ".")
		idList[index] = s1[0]
	}

	getDetailContent(ctx, db, idList)
}

func partitionTheTask(ctxt context.Context, baseUrl string, task *int) {
	// open first page
	openFirstPage(ctxt, baseUrl)
	maxPage := getMaxPageNumber(ctxt)
	pageType := getCurrentType(ctxt)
	fmt.Printf("Ready for partition. %d page in %s.\n", maxPage, pageType)

	//TODO, just for test. Delete when actual use.
	maxPage = testMaxPage

	startPage := 1
	motherUrl := baseUrl
	for startPage < maxPage {
		sonPart := fmt.Sprintf("&startPage=%d&task=%d", startPage, *task)
		sonUrl := motherUrl + sonPart
		fmt.Println("Add url for MedicalList")
		*task += 1
		fmt.Println("partition url: ", sonUrl)

		startPage += OnePartition
	}
}

func startGet(sonUrl string, startPage int) {
	fmt.Printf("Start get from page %d in the %s.\n", startPage, sonUrl)

	options := []chromedp.ExecAllocatorOption{
		chromedp.Flag("headless", false),
		chromedp.Flag("hide-scrollbars", false),
		chromedp.Flag("mute-audio", false),
		chromedp.UserAgent(`Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/80.0.3987.163 Chrome/80.0.3987.163 Safari/537.36`),
		//chromedp.ProxyServer("http://127.0.0.1:8080"),
	}
	options = append(chromedp.DefaultExecAllocatorOptions[:], options...)
	//创建chrome窗口
	allocCtx, cancel := chromedp.NewExecAllocator(context.Background(), options...)
	defer cancel()
	//create context
	ctxt, cancel := chromedp.NewContext(allocCtx)
	defer cancel()

	// open first page
	openFirstPage(ctxt, sonUrl)
	//printPageTitle(ctxt)
	fmt.Println(getCurrentType(ctxt))

	// get start page
	fmt.Println("Get start page: ", startPage)

	// get the max page number
	pageMaxInt := getMaxPageNumber(ctxt)
	//fmt.Println(pageMaxInt)

	// TODO, Delete this when actual use.
	pageMaxInt = testMaxPage

	if pageMaxInt > startPage + OnePartition - 1 {
		pageMaxInt = startPage + OnePartition - 1
	}

	db, err := gorm.Open(dbType, dbUrl)
	if err != nil {
		panic("Failed to connect to database")
	}
	defer db.Close()

	currentPage := startPage
	for currentPage <= pageMaxInt {
		resFlag := devPage(ctxt, currentPage)
		if resFlag {
			fmt.Printf("Success jump to page %d.[partition: %d]\n", currentPage, startPage/OnePartition)
			getContent(ctxt, db)
			time.Sleep(1 * time.Second)
			currentPage += 1
		}else {
			fmt.Println("Some thing wrong when jump page, retry...")
			time.Sleep(12 * time.Second)
			openFirstPage(ctxt, sonUrl)
		}
	}
	fmt.Println("Finished get ", getCurrentType(ctxt))

}

func partitionRequest(targetUrl string) {
	options := []chromedp.ExecAllocatorOption{
		chromedp.Flag("headless", true),
		chromedp.Flag("hide-scrollbars", false),
		chromedp.Flag("mute-audio", false),
		chromedp.Flag("disable-gpu", true),
		chromedp.Flag("enable-automation", false),
		chromedp.Flag("restore-on-startup", false),
		chromedp.WindowSize(1368, 768),
		chromedp.UserAgent(`Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/80.0.3987.163 Chrome/80.0.3987.163 Safari/537.36`),
		//chromedp.ProxyServer("http://127.0.0.1:8080"),
	}
	options = append(chromedp.DefaultExecAllocatorOptions[:], options...)
	//创建chrome窗口
	allocCtx, cancel := chromedp.NewExecAllocator(context.Background(), options...)
	defer cancel()
	//create context
	ctxt, cancel := chromedp.NewContext(allocCtx)
	defer cancel()

	// open first page
	openFirstPage(ctxt, targetUrl)
	maxPage := getMaxPageNumber(ctxt)
	pageType := getCurrentType(ctxt)
	fmt.Printf("Ready for partition. %d page in %s.\n", maxPage, pageType)

	//TODO, just for test. Delete when actual use.
	maxPage = testMaxPage

	startPage := 1
	for startPage <= maxPage {
		// Start as Concurrent
		startGet(targetUrl, startPage)

		startPage += OnePartition
	}
}

var taskId int
var paraTableName, resTableName, dbType string
var dbUrl string
var dbUser, dbPassword, dbDatabase, dbChar, dbHost, dbPort string

func main() {
	// ./medicine -paras=go_para_000002

	flag.StringVar(&paraTableName, "paras", "paras_id", "爬虫参数表id")

	flag.Parse()
	if flag.NFlag() < 1 {
		fmt.Println(flag.NArg())
		flag.Usage()
		return
	}

	fmt.Println("Start get medicine info...")
	table25 := table{"tableId": "25", "tableName": "TABLE25", "title": "国产药品", "bcId": "152904713761213296322795806604"}
	table32 := table{"tableId": "32", "tableName": "TABLE32", "title": "国产药品商品名", "bcId": "152904813882776432084296368957"}
	table36 := table{"tableId": "36", "tableName": "TABLE36", "title": "进口药品", "bcId": "152904858822343032639340277073"}
	table34 := table{"tableId": "34", "tableName": "TABLE34", "title": "药品生产企业", "bcId": "152911762991938722993241728138"}
	table138 := table{"tableId": "138", "tableName": "TABLE138", "title": "国家基本药物（2018年版）", "bcId": "152911951192978460689645865168"}

	tableList := []table{table25, table32, table36, table34, table138}

	for _, oneTable := range tableList {
		fmt.Println(oneTable["title"])

		v := url.Values{}
		for key, value := range oneTable{
			v.Add(key, value)
		}

		u := &url.URL{
			Scheme:   "http",
			Host:     "qy1.sfda.gov.cn",
			Path:     "datasearchcnda/face3/base.jsp",
			RawQuery: v.Encode(),
		}
		searchUrl := u.String()
		fmt.Println(searchUrl)
		partitionRequest(searchUrl)
	}
}

