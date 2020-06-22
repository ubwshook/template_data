package main

import (
	"encoding/json"
	"fmt"
	"github.com/globalsign/mgo/bson"
	"net/url"
	"runtime/debug"
	"strconv"
	"strings"
	"time"

	"github.com/gocolly/colly"
	"github.com/gocolly/colly/queue"

	"spiders/config"
	"spiders/database"
)

const URL = "https://restapi.amap.com/v3/place/text?keywords=%s&city=%s&key=%s"
const CITY = "西安"
//const KEY = "29be3b94d63b389134048d757e3fcc8b"
const KEY = "9280b7a213f3e018bacfd187e5a34e0e"

type Poi struct {
	ID string  `json:"id"`
	Name string  `json:"name"`
	Type string   `json:"type"`
	Address interface{}   `json:"address"`
	Location string   `json:"location"`
	Tel interface{}   `json:"tel"`
	PName string   `json:"pname"`
	CityName string  `json:"cityname"`
	AdName string  `json:"adname"`
}

type SearchResult struct {
	Status string  `json:"status"`
	Count string  `json:"count"`
	Info string  `json:"info"`
	InfoCode string  `json:"infocode"`
	PoiS []Poi  `json:"pois"`
}

type MongoResult struct {
	Id          bson.ObjectId  `json:"_id" bson:"_id"`
	ID          string         `json:"id" bson:"id"`
	TaskId      string         `json:"task_id" bson:"task_id"`
	Name        string         `json:"name" bson:"name"`
	Type        string         `json:"type" bson:"type"`
	Address     string         `json:"address" bson:"address"`
	Location    string         `json:"location" bson:"location"`
	Tel         string         `json:"tel" bson:"tel"`
	PName       string         `json:"p_name" bson:"p_name"`
	CityName    string         `json:"city_name" bson:"city_name"`
	AdName      string         `json:"ad_name" bson:"ad_name"`
	Page        int            `json:"page" bson:"page"`
}

type Parameter struct {
	Id              bson.ObjectId        `json:"_id" bson:"_id"`
	TemplateId      int                  `json:"templateId" bson:"templateId"`
	SpiderId        int                  `json:"spiderId" bson:"spiderId"`

	HeadersList     []string             `json:"headersList" bson:"headersList"`
	ParameterMap    map[string][]string  `json:"parameterMap" bson:"parameterMap"`
}

func insertSearchResult(poi Poi, page int) {
	var telStr string
	if tel, ok := poi.Tel.(string); ok {
		telStr = tel
	} else if tel, ok := poi.Tel.([]string); ok {
		telStr = strings.Join(tel, ",")
	} else {
		telStr = ""
	}

	var addressStr string
	if tel, ok := poi.Address.(string); ok {
		addressStr = tel
	} else if tel, ok := poi.Address.([]string); ok {
		addressStr = strings.Join(tel, ",")
	} else {
		addressStr = ""
	}

	var contentDb = MongoResult{
		Id:bson.NewObjectId(),
		ID:poi.ID,
		Name:poi.Name,
		Type:poi.Type,
		Address:addressStr,
		Location:poi.Location,
		Tel:telStr,
		PName:poi.PName,
		CityName:poi.CityName,
		AdName:poi.AdName,
		Page:page,
	}
	fmt.Println(contentDb)
	database.SaveItems(&contentDb)
}

func main() {
	// GOOS=linux GOARCH=amd64 go build -o a_map_amd64
	// GOOS=linux GOARCH=arm64 go build -o a_map_arm64
	// a_map.exe -paras=5ed9e77fa0a6cd055734386c

	fmt.Println("Spider amap start...")

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
		fmt.Printf("get spider error: %s, _id: %s", err.Error(), cmd.ParasTableId)
		debug.PrintStack()
		return
	}

	keywords := mongoPara.ParameterMap["keyword"]

	// Instantiate default collector
	c := colly.NewCollector()

	err = c.Limit(&colly.LimitRule{
		DomainGlob:  "*restapi.amap.com*",
		Parallelism: 2,
		RandomDelay: 10 * time.Second,
	})

	// create a request queue with 2 consumer threads
	q, _ := queue.New(
		2, // Number of consumer threads
		&queue.InMemoryQueueStorage{MaxSize: 10000}, // Use default queue storage
	)

	c.OnRequest(func(r *colly.Request) {
		fmt.Println("visiting", r.URL)
	})

	c.OnResponse(func(r *colly.Response) {
		fmt.Println("Return Code:", r.StatusCode)

		//searchResult := make(map[string]interface{})
		var searchResult SearchResult
		err := json.Unmarshal(r.Body, &searchResult)
		if err != nil {
			fmt.Println("Failed Unmarshal json. ", err)
		} else {
			rawQuery := r.Request.URL.RawQuery
			fmt.Println(rawQuery)

			m, _ := url.ParseQuery(rawQuery)
			_, ok := m["page"]
			if ok {
				page := m["page"][0]
				poiSList := searchResult.PoiS
				for _, poi := range poiSList {
					pageInt, err := strconv.Atoi(page)
					if err != nil {
						fmt.Println("Failed to change page to number.")
					}
					insertSearchResult(poi, pageInt)
				}
			} else {
				count, err := strconv.Atoi(searchResult.Count)
				if err != nil {
					fmt.Println("Failed to get result number, return.")
				} else {
					fmt.Printf("Get %d results.\n", count)
					mainUrl := r.Request.URL.String()
					totalPage := count / 20 + 1
					for i:=1; i<= totalPage; i++ {
						newUrl := fmt.Sprintf("%s&page=%d", mainUrl, i)
						err := q.AddURL(newUrl)
						if err != nil {
							fmt.Printf("Failed to add url %s to queue. %s \n", newUrl, err)
						}
						//time.Sleep(time.Second * 10)
					}
				}
			}
		}

	})

	for _, keyword := range keywords {
		// Add URLs to the queue
		err := q.AddURL(fmt.Sprintf(URL, keyword, CITY, KEY))
		if err != nil {
			fmt.Println("Failed to add queue", err)
		}
	}

	// Consume URLs
	err = q.Run(c)
	if err != nil {
		fmt.Println("Failed to start spider. ", err)
	}

	//time.Sleep(time.Minute * 5)
}

