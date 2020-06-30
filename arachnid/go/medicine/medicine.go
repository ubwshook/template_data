package main

import (
	"context"
	"encoding/json"
	"fmt"
	"github.com/globalsign/mgo/bson"
	"io/ioutil"
	"log"
	"net/http"
	"net/url"
	"regexp"
	"runtime/debug"
	"strconv"
	"strings"
	"time"

	"github.com/chromedp/cdproto/page"
	"github.com/chromedp/chromedp"

	"spiders/config"
	"spiders/database"
)

//const DevtoolsUrl string = "http://localhost:9222"
const OnePartition int = 5
const MaxPage int = 10

type table map[string]string

type Content struct {
	Id          bson.ObjectId  `json:"_id" bson:"_id"`
	TaskId      string         `json:"task_id" bson:"task_id"`
	MedicId     string         `json:"medic_id" bson:"medic_id"`
	Type        string         `json:"type" bson:"type"`
	Content     string         `json:"content" bson:"content"`
	Page        int            `json:"page" bson:"page"`
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

func formatDetailInfo(content string, medicId string, currentType string, pagePoint int) {
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

	//输出格式
	fmt.Println("Success to get one result. :", medic.Id)
	var contentDb = Content{
		Id:bson.NewObjectId(),
		MedicId:medic.Id,
		Type:medic.Type,
		Content:medic.Content,
		Page:medic.Page,
	}
	fmt.Println(contentDb)
	database.SaveItems(&contentDb)
}

func getDetailInfo(ctx context.Context, code string, medicId string, currentType string, pagePoint int) bool {
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
	formatDetailInfo(content, medicId, currentType, pagePoint)

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

func getDetailContent(ctx context.Context, idList [15]string) {
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
		getDetailInfo(ctx, jsCode, idList[index], currentType, currentPage)
		time.Sleep(1 * time.Second)
	}
}

func getContent(ctx context.Context) {
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

	getDetailContent(ctx, idList)
}

func startGet(sonUrl string, startPage int, pageMaxInt int) {
	fmt.Printf("Start get from page %d in the %s.\n", startPage, sonUrl)

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
	openFirstPage(ctxt, sonUrl)
	//printPageTitle(ctxt)
	fmt.Println(getCurrentType(ctxt))

	// get start page
	fmt.Println("Get start page: ", startPage)

	if pageMaxInt > startPage + OnePartition - 1 {
		pageMaxInt = startPage + OnePartition - 1
	}

	currentPage := startPage
	for currentPage <= pageMaxInt {
		resFlag := devPage(ctxt, currentPage)
		if resFlag {
			fmt.Printf("Success jump to page %d.[partition: %d]\n", currentPage, startPage/OnePartition)
			getContent(ctxt)
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

func partitionRequest(targetUrl string, maxPage int) {
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
	// 取最大值
	if maxPage == -1 {
		maxPage = getMaxPageNumber(ctxt)
	}
	pageType := getCurrentType(ctxt)
	fmt.Printf("Ready for partition. %d page in %s.\n", maxPage, pageType)

	startPage := 1
	for startPage <= maxPage {
		// Start as Concurrent
		startGet(targetUrl, startPage, maxPage)

		startPage += OnePartition
	}
}

type Parameter struct {
	Id              bson.ObjectId        `json:"_id" bson:"_id"`
	TemplateId      int                  `json:"templateId" bson:"templateId"`
	SpiderId        int                  `json:"spiderId" bson:"spiderId"`

	HeadersList     []string             `json:"headersList" bson:"headersList"`
	ParameterMap    map[string][]string  `json:"parameterMap" bson:"parameterMap"`
}

func main() {
	// GOOS=linux GOARCH=amd64 go build -o medicine_amd64
	// GOOS=linux GOARCH=arm64 go build -o medicine_arm64
	// ./medicine -paras=5ed9e77fa0a6cd055734386c

	fmt.Println("Spider medicine info start...")

	var cmd = new(config.CmdConfig)
	err := cmd.ReadCmdParameter()
	if err != nil {
		fmt.Println(err)
		debug.PrintStack()
		return
	}

	// 初始化mongo
	if err := database.InitMongo(); err != nil {
		fmt.Println(err.Error())
		fmt.Println("Failed to connect to mongo")
	}

	sess, col := database.GetCol("parameters")
	defer sess.Close()

	var mongoPara *Parameter
	bson.ObjectIdHex(cmd.ParasTableId)
	if err := col.Find(bson.M{"_id": bson.ObjectIdHex(cmd.ParasTableId)}).One(&mongoPara); err != nil {
		fmt.Printf("get spider error: %s, _id: %s \n", err.Error(), cmd.ParasTableId)
		debug.PrintStack()
		return
	}

	keywords := mongoPara.ParameterMap["keyword"]
	pages := mongoPara.ParameterMap["page"]

	fmt.Println("Start get medicine info...")
	table25 := table{"tableId": "25", "tableName": "TABLE25", "title": "国产药品", "bcId": "152904713761213296322795806604"}
	table32 := table{"tableId": "32", "tableName": "TABLE32", "title": "国产药品商品名", "bcId": "152904813882776432084296368957"}
	table36 := table{"tableId": "36", "tableName": "TABLE36", "title": "进口药品", "bcId": "152904858822343032639340277073"}
	table34 := table{"tableId": "34", "tableName": "TABLE34", "title": "药品生产企业", "bcId": "152911762991938722993241728138"}
	table138 := table{"tableId": "138", "tableName": "TABLE138", "title": "国家基本药物（2018年版）", "bcId": "152911951192978460689645865168"}

	tableMap := make(map[string]table)
	tableMap["国产药品"] = table25
	tableMap["国产药品商品名"] = table32
	tableMap["进口药品"] = table36
	tableMap["药品生产企业"] = table34
	tableMap["国家基本药物"] = table138

	var tableList []table
	var pageList []int
	// TODO, 合法性处理需要完善
	for i, key := range keywords {
		// 获取最大页数
		pageStr := pages[i]
		pageInt := MaxPage
		if pageStr == "" {
			pageInt = MaxPage
		} else if pageStr == "max" || pageStr == "all" {
			pageInt = -1
		} else {
			pageInt, err = strconv.Atoi(pageStr)
			if err != nil {
				fmt.Printf("The max page %s is not support, set as default[%d].", pageStr, MaxPage)
			}
		}
		// 获取对应页面信息
		tableTag, ok := tableMap[key]
		if ! ok {
			fmt.Printf("The keyword %s is not supoort.", key)
			continue
		}
		pageList = append(pageList, pageInt)
		tableList = append(tableList, tableTag)
	}

	for i, oneTable := range tableList {
		fmt.Println(oneTable["title"])

		v := url.Values{}
		for key, value := range oneTable{
			v.Add(key, value)
		}

		u := &url.URL{
			Scheme:   "http",
			Host:     "app1.nmpa.gov.cn",
			Path:     "datasearchcnda/face3/base.jsp",
			RawQuery: v.Encode(),
		}
		searchUrl := u.String()
		fmt.Println(searchUrl)
		partitionRequest(searchUrl, pageList[i])
	}
}

