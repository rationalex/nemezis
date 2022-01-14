package main

import (
	"fmt"
	"github.com/PuerkitoBio/goquery"
	"log"
	"net/http"
	"net/http/cookiejar"
	"net/url"
	"strings"
)

const ejudgeRawURL = "https://ejudge.algocode.ru/cgi-bin/serve-control"

func arrayOf(root *goquery.Selection, selector string) []*goquery.Selection {
	ret := make([]*goquery.Selection, 0)

	sel := root.Find(selector)
	for i := range sel.Nodes {
		node := sel.Eq(i)
		ret = append(ret, node)
	}

	return ret
}

func main() {
	cookieJar, _ := cookiejar.New(nil)
	client := http.Client{Jar: cookieJar}

	params := url.Values{}
	params.Add("SID", "0000000000000000")
	params.Add("login", "rationalex")
	params.Add("password", "d71rr2LnBiMUtqEz")
	params.Add("submit", "Log+in")

	req, err := http.NewRequest("POST", ejudgeRawURL, strings.NewReader(params.Encode()))
	if err != nil {
		log.Fatalf("can't create ejudge login request: %v", err)
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")

	resp, err := client.Do(req)
	if err != nil {
		log.Fatalf("ejudge login request failed: %v", err)
	}
	defer resp.Body.Close()

	//ejURL, _ := url.Parse(ejudgeRawURL)
	//SID := cookieJar.Cookies(ejURL)[0].Value
	doc, err := goquery.NewDocumentFromReader(resp.Body)

	rows := arrayOf(doc.Selection, "tr")[2:] // skip contest management buttons and table header
	for _, row := range rows {
		// 0:N
		// 1:ID
		// 2:Name
		// 3:Details
		// 4:Users
		// 5:Settings
		// 6:Tests
		// 7:Judge
		// 8:Master
		// 9:User

		fmt.Println(arrayOf(arrayOf(row, "td")[8], "a")[0].Attr("href"))
		//masterRequestParams := url.Values{}
		//masterRequestParams.Add("action", "3")
		//masterRequestParams.Add("SID", SID)
		//masterRequestParams.Add("contest_id", )
		//
		//req, err := http.NewRequest("GET", "https://ejudge.algocode.ru/cgi-bin/new-master", strings.NewReader(masterRequestParams.Encode()))
		//if err != nil {
		//	log.Fatalf("can't create contest master page request: %v", err)
		//}
		//req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
		//
		//resp, err := client.Do(req)
		//if err != nil {
		//	log.Fatalf("request to contest master page failed: %v", err)
		//}
		//defer resp.Body.Close()
		//
		//doc, err := goquery.NewDocumentFromReader(resp.Body)
		//fmt.Println(doc.Text())
	}
}
