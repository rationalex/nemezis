package ejudge

type Problem struct {
	name string
}

type Contest struct {
	ID       int
	FullName string
	Topic    string
	Problems []Problem
}
