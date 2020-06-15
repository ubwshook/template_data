package database

import (
	"net"
	"os"
	"time"

	"github.com/globalsign/mgo"
)

var Session *mgo.Session

func GetSession() *mgo.Session {
	return Session.Copy()
}

func GetDb() (*mgo.Session, *mgo.Database) {
	s := GetSession()
	return s, s.DB(getOsEnvWithDefault("CRAWLAB_MONGO_DB", "crawlab_test"))
}

func GetCol(collectionName string) (*mgo.Session, *mgo.Collection) {
	s := GetSession()
	db := s.DB(getOsEnvWithDefault("CRAWLAB_MONGO_DB", "crawlab_test"))
	col := db.C(collectionName)
	return s, col
}

func GetResultCol() (*mgo.Session, *mgo.Collection) {
	s := GetSession()
	db := s.DB(getOsEnvWithDefault("CRAWLAB_MONGO_DB", "crawlab_test"))
	col := db.C(getOsEnvWithDefault("CRAWLAB_COLLECTION", "result_test"))
	return s, col
}

func getOsEnvWithDefault(key, defVal string) string {
	val, ex := os.LookupEnv(key)
	if !ex {
		return defVal
	}
	return val
}

func InitMongo() error {
	var mongoHost = getOsEnvWithDefault("CRAWLAB_MONGO_HOST", "127.0.0.1")
	var mongoPort = getOsEnvWithDefault("CRAWLAB_MONGO_PORT", "27017")
	var mongoDb = getOsEnvWithDefault("CRAWLAB_MONGO_DB", "crawlab_test")
	var mongoUsername = getOsEnvWithDefault("CRAWLAB_MONGO_USERNAME", "")
	var mongoPassword = getOsEnvWithDefault("CRAWLAB_MONGO_PASSWORD", "")
	var mongoAuth = getOsEnvWithDefault("CRAWLAB_MONGO_AUTHSOURCE", "")

	if Session == nil {
		var dialInfo mgo.DialInfo
		addr := net.JoinHostPort(mongoHost, mongoPort)
		timeout := time.Second * 10
		dialInfo = mgo.DialInfo{
			Addrs:         []string{addr},
			Timeout:       timeout,
			Database:      mongoDb,
			PoolLimit:     100,
			PoolTimeout:   timeout,
			ReadTimeout:   timeout,
			WriteTimeout:  timeout,
			AppName:       "crawlab",
			FailFast:      true,
			MinPoolSize:   10,
			MaxIdleTimeMS: 1000 * 30,
		}
		if mongoUsername != "" {
			dialInfo.Username = mongoUsername
			dialInfo.Password = mongoPassword
			dialInfo.Source = mongoAuth
		}

		// mongo session
		var sess *mgo.Session

		// 错误次数
		errNum := 0

		// 重复尝试连接mongo
		for {
			var err error

			// 连接mongo
			sess, err = mgo.DialWithInfo(&dialInfo)

			if err != nil {
				// 如果连接错误，休息1秒，错误次数+1
				time.Sleep(1 * time.Second)
				errNum++

				// 如果错误次数超过30，返回错误
				if errNum >= 30 {
					return err
				}
			} else {
				// 如果没有错误，退出循环
				break
			}
		}

		// 赋值给全局mongo session
		Session = sess
	}

	return nil
}
