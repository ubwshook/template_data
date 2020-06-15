package database

import (
	"fmt"
	"github.com/globalsign/mgo/bson"
	"os"
	"reflect"
)

const (
	OVERWRITE = "overwrite"
	IGNORE = "ignore"
)

func getTaskId() string {
	val, ex := os.LookupEnv("CRAWLAB_TASK_ID")
	if !ex {
		return "000000000001"
	}
	return val
}

func getIsDedup() string {
	val, ex := os.LookupEnv("CRAWLAB_IS_DEDUP")
	if !ex {
		return "0"
	}
	return val
}

func getDedupField() string {
	val, ex := os.LookupEnv("CRAWLAB_DEDUP_FIELD")
	if !ex {
		return "ID"
	}
	return val
}

func getDedupMethod() string {
	return os.Getenv("CRAWLAB_DEDUP_METHOD")
}

func SaveItems(itemStruct interface{}) {
	itemType := reflect.TypeOf(itemStruct)
	itemValue := reflect.ValueOf(itemStruct)

	taskId := getTaskId()

	// 通过反射更新传入结构中task id的值
	if itemType.Kind() == reflect.Ptr {
		if _, flag :=itemType.Elem().FieldByName("TaskId"); flag {
			itemValue = itemValue.Elem()
			fieldTaskId := itemValue.FieldByName("TaskId")
			fieldTaskId.SetString(taskId)
		} else {
			fmt.Println("There is no task id in the struct.")
			return
		}

		isDedup := getIsDedup()

		s, c := GetResultCol()
		defer s.Close()

		if isDedup == "1" {
			dedupField := getDedupField()
			dedupMethod := getDedupMethod()

			if dedupMethod == OVERWRITE {
				// 覆盖
				if num, _ := c.Find(bson.M{dedupField: itemValue.FieldByName(dedupField)}).Count(); num != 0 {
					fmt.Println("Replace...")
					fmt.Println(itemStruct)
					if err := c.Update(bson.M{dedupField: itemValue.FieldByName(dedupField)}, itemStruct); err != nil {
						fmt.Println(err.Error())
					}
				} else {
					fmt.Println(itemStruct)
					if err := c.Insert(itemStruct); err != nil {
						fmt.Println(err.Error())
					}
				}
			} else if dedupMethod == IGNORE {
				fmt.Println(itemStruct)
				if err := c.Insert(itemStruct); err != nil {
					fmt.Println(err.Error())
				}
			} else {
				fmt.Println(itemStruct)
				if err := c.Insert(itemStruct); err != nil {
					fmt.Println(err.Error())
				}
			}
		} else {
			fmt.Println(itemStruct)
			if err := c.Insert(itemStruct); err != nil {
				fmt.Println(err.Error())
			}
		}
	}
}
